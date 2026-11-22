"""Pluggable transcription backends (faster-whisper & OpenAI/Groq Cloud)."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Any, Callable, Optional

from ..utils.exceptions import TranscriptionError
from ..utils.formatters import SubtitleFormatterFactory, SubtitleSegment, WordTiming
from .transcriber import TranscriberStrategy, TranscriptionResult, WhisperCppTranscriber

logger = logging.getLogger(__name__)


class FasterWhisperTranscriber(TranscriberStrategy):
    """CTranslate2-backed local transcription via optional ``faster-whisper``."""

    def __init__(
        self,
        device: str = "auto",
        compute_type: str = "auto",
        vad: bool = True,
        word_timestamps: bool = False,
        beam_size: int = 5,
    ):
        try:
            import faster_whisper  # type: ignore  # noqa: F401
        except ImportError as e:
            raise TranscriptionError(
                "Backend `faster-whisper` requires the optional extra. "
                "Install with: pip install 'subtitle-generator[faster-whisper]'",
                cause=e,
            )
        self.device = device
        self.compute_type = compute_type
        self.vad = vad
        self.word_timestamps = word_timestamps
        self.beam_size = beam_size

    def get_supported_formats(self) -> list[str]:
        return ["vtt", "srt", "ass", "ttml", "txt", "json", "lrc", "csv"]

    def transcribe(
        self,
        input_path: str,
        model_path: str,
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        from faster_whisper import WhisperModel  # type: ignore

        process_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)
        model_name = kwargs.get("model_name") or model_path
        if model_name == "turbo":
            model_name = "large-v3-turbo"
        elif model_name == "large":
            model_name = "large-v3"

        if progress_callback:
            progress_callback("transcribing", 0.0)

        try:
            model = WhisperModel(
                model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            seg_iter, info = model.transcribe(
                input_path,
                language=None if language in {None, "", "auto"} else language,
                task="translate" if translate else "transcribe",
                initial_prompt=prompt,
                vad_filter=kwargs.get("vad", self.vad),
                word_timestamps=kwargs.get("word_timestamps", self.word_timestamps),
                beam_size=self.beam_size,
            )

            segments: list[SubtitleSegment] = []
            total_dur = float(getattr(info, "duration", 0.0) or 0.0)
            for idx, s in enumerate(seg_iter, 1):
                words = [
                    WordTiming(
                        word=w.word.strip(),
                        start_time=float(w.start),
                        end_time=float(w.end),
                        probability=float(getattr(w, "probability", 1.0)),
                    )
                    for w in (getattr(s, "words", None) or [])
                    if getattr(w, "word", "").strip()
                ]
                segments.append(
                    SubtitleSegment(
                        index=idx,
                        start_time=float(s.start),
                        end_time=float(s.end),
                        text=str(s.text).strip(),
                        words=words,
                    )
                )
                if progress_callback and total_dur > 0:
                    progress_callback("transcribing", min(0.99, float(s.end) / total_dur))

            formatter = SubtitleFormatterFactory.create(output_format)
            out_path = os.path.join(output_dir, f"{process_id}.{formatter.file_extension}")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(formatter.format(segments))

            if progress_callback:
                progress_callback("transcribing", 1.0)

            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path=out_path,
                format=output_format,
                success=True,
                output_paths={output_format: out_path},
            )
        except Exception as e:
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=output_format,
                success=False,
                error=str(e),
            )


class CloudTranscriber(TranscriberStrategy):
    """OpenAI or Groq Whisper API transcription via optional ``openai`` SDK."""

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        try:
            import openai  # type: ignore  # noqa: F401
        except ImportError as e:
            raise TranscriptionError(
                f"Cloud backend `{provider}` requires `openai`. "
                "Install with: pip install 'subtitle-generator[cloud]'",
                cause=e,
            )
        self.provider = provider.lower()
        if self.provider == "groq":
            self.api_key = api_key or os.environ.get("GROQ_API_KEY")
            self.base_url: Optional[str] = "https://api.groq.com/openai/v1"
            self.model = model or "whisper-large-v3-turbo"
            env_hint = "GROQ_API_KEY"
        else:
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.base_url = None
            self.model = model or "whisper-1"
            env_hint = "OPENAI_API_KEY"

        if not self.api_key:
            raise TranscriptionError(
                f"Missing API key for {self.provider}. Set {env_hint} in your environment."
            )

    def get_supported_formats(self) -> list[str]:
        return ["vtt", "srt", "ass", "ttml", "txt", "json", "lrc", "csv"]

    def transcribe(
        self,
        input_path: str,
        model_path: str,
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        import openai  # type: ignore

        process_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)
        temp_mp3: Optional[str] = None

        if progress_callback:
            progress_callback("transcribing", 0.0)

        try:
            upload_path = input_path
            # Compress large files (>24 MB) to mono 64kbps MP3 for API size limits
            if os.path.getsize(input_path) > 24 * 1024 * 1024:
                from .video_processor import VideoProcessor

                fd, temp_mp3 = tempfile.mkstemp(prefix="sg_cloud_", suffix=".mp3", dir=output_dir)
                os.close(fd)
                VideoProcessor(overwrite_output=True).extract_audio(
                    input_path, output_path=temp_mp3, audio_format="mp3", sample_rate=16000
                )
                upload_path = temp_mp3

            client_kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            client = openai.OpenAI(**client_kwargs)

            with open(upload_path, "rb") as audio_file:
                if translate:
                    resp = client.audio.translations.create(
                        model=self.model,
                        file=audio_file,
                        response_format="verbose_json",
                        prompt=prompt or "",
                    )
                else:
                    api_kwargs: dict[str, Any] = {
                        "model": self.model,
                        "file": audio_file,
                        "response_format": "verbose_json",
                    }
                    if language and language != "auto":
                        api_kwargs["language"] = language
                    if prompt:
                        api_kwargs["prompt"] = prompt
                    resp = client.audio.transcriptions.create(**api_kwargs)

            raw_segments = getattr(resp, "segments", None) or []
            segments: list[SubtitleSegment] = []
            for idx, s in enumerate(raw_segments, 1):
                start = float(s.get("start", 0.0) if isinstance(s, dict) else getattr(s, "start", 0.0))
                end = float(s.get("end", 0.0) if isinstance(s, dict) else getattr(s, "end", 0.0))
                text = str(s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")).strip()
                segments.append(SubtitleSegment(index=idx, start_time=start, end_time=end, text=text))

            formatter = SubtitleFormatterFactory.create(output_format)
            out_path = os.path.join(output_dir, f"{process_id}.{formatter.file_extension}")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(formatter.format(segments))

            if progress_callback:
                progress_callback("transcribing", 1.0)

            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path=out_path,
                format=output_format,
                success=True,
                output_paths={output_format: out_path},
            )
        except Exception as e:
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=output_format,
                success=False,
                error=str(e),
            )
        finally:
            if temp_mp3 and os.path.exists(temp_mp3):
                try:
                    os.remove(temp_mp3)
                except OSError:
                    pass


def create_transcriber(backend: str = "whisper.cpp", **kwargs: Any) -> TranscriberStrategy:
    """Factory that instantiates the requested transcription backend."""
    name = (backend or "whisper.cpp").strip().lower()
    if name in {"whisper.cpp", "whispercpp", "local"}:
        return WhisperCppTranscriber(**kwargs)
    if name in {"faster-whisper", "faster_whisper", "ctranslate2"}:
        return FasterWhisperTranscriber(
            vad=kwargs.get("vad", True),
            word_timestamps=kwargs.get("word_timestamps", False),
            beam_size=kwargs.get("beam_size") or 5,
        )
    if name in {"openai", "groq"}:
        return CloudTranscriber(provider=name, model=kwargs.get("cloud_model"))
    raise TranscriptionError(
        f"Unknown backend: {backend}. Choose from: whisper.cpp, faster-whisper, openai, groq"
    )
