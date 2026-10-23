"""Transcriber strategy and the whisper.cpp implementation."""

import logging
import os
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

from ..utils.exceptions import TranscriptionError
from ..utils.file_handler import get_file_extension
from ..utils.paths import find_whisper_binary, whisper_binary_install_hint
from ..utils.validators import VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    process_id: str
    input_path: str
    output_path: str
    format: str
    success: bool
    error: Optional[str] = None


class TranscriberStrategy(ABC):
    @abstractmethod
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
    ) -> TranscriptionResult:
        ...

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        ...


class WhisperCppTranscriber(TranscriberStrategy):
    """Calls the whisper.cpp `whisper-cli` binary."""

    _FORMAT_FLAGS = {
        "vtt": "-ovtt",
        "srt": "-osrt",
        "txt": "-otxt",
        "json": "-oj",
        "lrc": "-olrc",
        "csv": "-ocsv",
    }

    # Cache binary path -> whether it supports `-vi` / `--video-input`
    _vi_support_cache: dict[str, bool] = {}

    def __init__(
        self,
        binary_path: Optional[str] = None,
        threads: int = 4,
        processors: int = 1,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
    ):
        resolved = find_whisper_binary(binary_path)
        if not resolved:
            raise TranscriptionError(
                whisper_binary_install_hint(),
                details={"explicit_binary_path": binary_path, "cwd": os.getcwd()},
            )
        self.binary_path = resolved
        self.threads = threads
        self.processors = processors
        self.language = language
        self.translate = translate
        self.max_len = max_len
        self.split_on_word = split_on_word
        self.prompt = prompt

    def get_supported_formats(self) -> list[str]:
        return list(self._FORMAT_FLAGS.keys())

    def supports_video_input(self) -> bool:
        """Check whether the resolved `whisper-cli` binary supports `-vi`."""
        if self.binary_path in self._vi_support_cache:
            return self._vi_support_cache[self.binary_path]

        try:
            proc = subprocess.run(
                [self.binary_path, "-h"],
                check=False,
                capture_output=True,
                timeout=10,
            )
            help_text = (
                (proc.stdout or b"").decode("utf-8", errors="replace")
                + "\n"
                + (proc.stderr or b"").decode("utf-8", errors="replace")
            )
            # If `-h` produced help output, check for `-vi` / `--video-input`.
            # If `-h` returned empty output (e.g. a stub script in unit tests),
            # default to True.
            if help_text.strip():
                supported = "-vi" in help_text or "--video-input" in help_text
            else:
                supported = True
        except Exception:
            supported = True

        self._vi_support_cache[self.binary_path] = supported
        return supported

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
    ) -> TranscriptionResult:
        process_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)
        output_base = os.path.join(output_dir, process_id)

        output_flag = self._FORMAT_FLAGS.get(output_format, "-ovtt")
        actual_format = output_format if output_format in self._FORMAT_FLAGS else "vtt"

        effective_lang = language if language is not None else self.language
        effective_translate = translate or self.translate
        effective_max_len = max_len if max_len > 0 else self.max_len
        effective_split_on_word = split_on_word or self.split_on_word
        effective_prompt = prompt if prompt is not None else self.prompt

        ext = get_file_extension(input_path)
        is_video = ext in VIDEO_EXTENSIONS
        use_vi = self.supports_video_input()

        temp_wav_path: Optional[str] = None
        actual_input = input_path

        if is_video and not use_vi:
            logger.info(
                "Binary %s does not advertise -vi; extracting 16kHz mono WAV via FFmpeg",
                self.binary_path,
            )
            from .video_processor import VideoProcessor

            fd, temp_wav_path = tempfile.mkstemp(
                prefix=f"sg_{process_id}_", suffix=".wav", dir=output_dir
            )
            os.close(fd)
            try:
                processor = VideoProcessor(overwrite_output=True)
                actual_input = processor.extract_audio(
                    video_path=input_path,
                    output_path=temp_wav_path,
                    audio_format="wav",
                    sample_rate=16000,
                )
            except Exception as e:
                if temp_wav_path and os.path.exists(temp_wav_path):
                    try:
                        os.remove(temp_wav_path)
                    except OSError:
                        pass
                return TranscriptionResult(
                    process_id=process_id,
                    input_path=input_path,
                    output_path="",
                    format=actual_format,
                    success=False,
                    error=f"Audio extraction fallback failed: {e}",
                )

        # argv list (no shell=True): handles spaces/quotes in filenames safely.
        argv = [
            self.binary_path,
            "-t", str(self.threads),
            "-p", str(self.processors),
            "-m", model_path,
        ]
        if use_vi:
            argv.append("-vi")
        if effective_lang:
            argv.extend(["-l", effective_lang])
        if effective_translate:
            argv.append("-tr")
        if effective_max_len and effective_max_len > 0:
            argv.extend(["-ml", str(effective_max_len)])
        if effective_split_on_word:
            argv.append("-sow")
        if effective_prompt:
            argv.extend(["--prompt", effective_prompt])
        argv.extend([
            "-f", actual_input,
            output_flag,
            "-of", output_base,
        ])

        if progress_callback:
            progress_callback("transcribing", 0.0)

        try:
            logger.info("Running transcription: %s", " ".join(argv))
            subprocess.run(argv, check=True, capture_output=True)
            if progress_callback:
                progress_callback("transcribing", 1.0)

            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path=f"{output_base}.{actual_format}",
                format=actual_format,
                success=True,
            )

        except FileNotFoundError as e:
            logger.error("Transcription failed: %s", e)
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=actual_format,
                success=False,
                error=whisper_binary_install_hint(),
            )
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace").strip()
            stdout = (e.stdout or b"").decode("utf-8", errors="replace").strip()
            error_msg = stderr or stdout or str(e)
            logger.error("Transcription failed: %s", error_msg)

            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=actual_format,
                success=False,
                error=error_msg,
            )
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass
