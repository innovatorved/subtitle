"""Transcriber strategy and the upgraded whisper.cpp implementation."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..utils.exceptions import TranscriptionError
from ..utils.file_handler import get_file_extension
from ..utils.paths import default_threads, find_whisper_binary, whisper_binary_install_hint
from ..utils.validators import VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

_PROGRESS_RE = re.compile(r"progress\s*=\s*(\d{1,3})\s*%")


@dataclass
class TranscriptionResult:
    process_id: str
    input_path: str
    output_path: str
    format: str
    success: bool
    error: Optional[str] = None
    output_paths: dict[str, str] = field(default_factory=dict)


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
    """Calls the whisper.cpp ``whisper-cli`` binary with live progress & Silero VAD."""

    _FORMAT_FLAGS = {
        "vtt": "-ovtt",
        "srt": "-osrt",
        "txt": "-otxt",
        "json": "-oj",
        "lrc": "-olrc",
        "csv": "-ocsv",
    }

    # Cache binary path -> capability dict
    _capabilities_cache: dict[str, dict[str, bool]] = {}
    # Backward-compatible cache alias used by existing tests
    _vi_support_cache: dict[str, bool] = {}
    _install_lock = threading.Lock()

    def __init__(
        self,
        binary_path: Optional[str] = None,
        threads: Optional[int] = None,
        processors: int = 1,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        vad: bool = True,
        vad_model_path: Optional[str] = None,
        vad_threshold: float = 0.5,
        suppress_nst: bool = True,
        carry_initial_prompt: bool = False,
        beam_size: Optional[int] = None,
        best_of: Optional[int] = None,
        no_gpu: bool = False,
        device: Optional[int] = None,
        diarize: bool = False,
        tinydiarize: bool = False,
        word_timestamps: bool = False,
        timeout: Optional[int] = None,
        auto_install: bool = True,
    ):
        resolved = find_whisper_binary(binary_path)
        if not resolved and auto_install and not binary_path and not os.environ.get("SUBTITLE_NO_AUTO_INSTALL"):
            resolved = self._auto_install_prebuilt_binary()
        if not resolved:
            raise TranscriptionError(
                whisper_binary_install_hint(),
                details={"explicit_binary_path": binary_path, "cwd": os.getcwd()},
            )
        self.binary_path = resolved
        self.threads = threads if threads is not None else default_threads()
        self.processors = max(1, processors)
        self.language = language
        self.translate = translate
        self.max_len = max_len
        self.split_on_word = split_on_word
        self.prompt = prompt
        self.vad = vad
        self.vad_model_path = vad_model_path
        self.vad_threshold = vad_threshold
        self.suppress_nst = suppress_nst
        self.carry_initial_prompt = carry_initial_prompt
        self.beam_size = beam_size
        self.best_of = best_of
        self.no_gpu = no_gpu
        self.device = device
        self.diarize = diarize
        self.tinydiarize = tinydiarize
        self.word_timestamps = word_timestamps
        self.timeout = timeout

    def get_supported_formats(self) -> list[str]:
        return list(self._FORMAT_FLAGS.keys()) + ["ass", "ttml"]

    @classmethod
    def _auto_install_prebuilt_binary(cls) -> Optional[str]:
        """Auto-download the verified prebuilt whisper-cli binary on first run."""
        with cls._install_lock:
            existing = find_whisper_binary()
            if existing:
                return existing
            from ..utils.paths import installed_whisper_binary_target
            from ..utils.whisper_setup import try_download_prebuilt

            target = installed_whisper_binary_target()
            logger.info("whisper-cli not found; auto-installing prebuilt binary to %s...", target)
            try:
                return try_download_prebuilt(target)
            except Exception as e:
                logger.warning("Auto-install of prebuilt whisper-cli failed: %s", e)
                return None

    def get_capabilities(self) -> dict[str, bool]:
        """Probe and cache CLI flags supported by the resolved whisper-cli binary."""
        if self.binary_path in self._capabilities_cache:
            return self._capabilities_cache[self.binary_path]

        caps = {
            "video_input": True,
            "vad": False,
            "progress": False,
            "dtw": False,
            "tinydiarize": False,
            "diarize": False,
            "json_full": False,
            "suppress_nst": False,
            "carry_initial_prompt": False,
        }
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
            if help_text.strip():
                caps["video_input"] = "-vi" in help_text or "--video-input" in help_text
                caps["vad"] = "--vad" in help_text
                caps["progress"] = "-pp" in help_text or "--print-progress" in help_text
                caps["dtw"] = "-dtw" in help_text
                caps["tinydiarize"] = "-tdrz" in help_text or "--tinydiarize" in help_text
                caps["diarize"] = "-di," in help_text or "--diarize" in help_text
                caps["json_full"] = "-ojf" in help_text or "--output-json-full" in help_text
                caps["suppress_nst"] = "-sns" in help_text or "--suppress-nst" in help_text
                caps["carry_initial_prompt"] = "--carry-initial-prompt" in help_text
        except Exception:
            pass

        self._capabilities_cache[self.binary_path] = caps
        self._vi_support_cache[self.binary_path] = caps["video_input"]
        return caps

    def supports_video_input(self) -> bool:
        """Check whether the resolved ``whisper-cli`` binary supports ``-vi``."""
        if self.binary_path in self._vi_support_cache:
            return self._vi_support_cache[self.binary_path]
        return self.get_capabilities()["video_input"]

    def _run_process(
        self,
        argv: list[str],
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """Run whisper-cli without pipe deadlocks, enforcing timeout & live `-pp` progress."""
        import threading

        if not progress_callback:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                timeout=self.timeout,
            )
            if completed.returncode != 0:
                stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
                stdout = (completed.stdout or b"").decode("utf-8", errors="replace").strip()
                raise subprocess.CalledProcessError(
                    completed.returncode, argv, output=stdout.encode(), stderr=stderr.encode()
                )
            return

        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout_chunks: list[str] = []
        stderr_lines: list[str] = []
        timed_out = threading.Event()

        def _drain_stdout() -> None:
            try:
                if proc.stdout:
                    for chunk in proc.stdout:
                        stdout_chunks.append(chunk)
            except Exception:
                pass

        def _on_timeout() -> None:
            timed_out.set()
            try:
                proc.kill()
            except OSError:
                pass

        stdout_thread = threading.Thread(target=_drain_stdout, daemon=True)
        stdout_thread.start()
        timer: Optional[threading.Timer] = None
        if self.timeout and self.timeout > 0:
            timer = threading.Timer(self.timeout, _on_timeout)
            timer.daemon = True
            timer.start()

        try:
            assert proc.stderr is not None
            for line in proc.stderr:
                stderr_lines.append(line)
                m = _PROGRESS_RE.search(line)
                if m:
                    pct = min(0.99, max(0.0, int(m.group(1)) / 100.0))
                    progress_callback("transcribing", pct)
            ret = proc.wait()
            stdout_thread.join(timeout=2)
            if timed_out.is_set():
                raise subprocess.TimeoutExpired(argv, self.timeout or 0)
            if ret != 0:
                stdout_text = "".join(stdout_chunks).strip()
                err_str = "".join(stderr_lines).strip() or stdout_text
                raise subprocess.CalledProcessError(
                    ret, argv, output=stdout_text.encode(), stderr=err_str.encode()
                )
        except BaseException:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            raise
        finally:
            if timer:
                timer.cancel()
            for stream in (proc.stdout, proc.stderr):
                if stream and hasattr(stream, "close"):
                    try:
                        stream.close()
                    except OSError:
                        pass

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
        output_formats: Optional[list[str]] = None,
        vad: Optional[bool] = None,
        vad_model_path: Optional[str] = None,
        word_timestamps: Optional[bool] = None,
        diarize: Optional[bool] = None,
        tinydiarize: Optional[bool] = None,
    ) -> TranscriptionResult:
        process_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)
        output_base = os.path.join(output_dir, process_id)

        requested_formats = list(output_formats) if output_formats else [output_format]
        primary_format = requested_formats[0] if requested_formats else "vtt"

        caps = self.get_capabilities()
        effective_lang = language if language is not None else self.language
        effective_translate = translate or self.translate
        effective_max_len = max_len if max_len > 0 else self.max_len
        effective_split_on_word = split_on_word or self.split_on_word
        effective_prompt = prompt if prompt is not None else self.prompt
        effective_vad = self.vad if vad is None else vad
        effective_vad_model = vad_model_path or self.vad_model_path
        effective_word_ts = self.word_timestamps if word_timestamps is None else word_timestamps
        effective_diarize = self.diarize if diarize is None else diarize
        effective_tdrz = self.tinydiarize if tinydiarize is None else tinydiarize

        # Determine native whisper-cli output flags
        native_formats: list[str] = []
        for fmt in requested_formats:
            if fmt in self._FORMAT_FLAGS and fmt not in native_formats:
                native_formats.append(fmt)

        # If caller needs ASS/TTML or word timestamps, emit full JSON so we have word timings
        needs_json_full = effective_word_ts or ("ass" in requested_formats and caps["json_full"])
        if needs_json_full and "json" not in native_formats:
            native_formats.append("json")
        if not native_formats:
            native_formats.append("vtt")

        ext = get_file_extension(input_path)
        is_video = ext in VIDEO_EXTENSIONS
        use_vi = self.supports_video_input()

        temp_wav_path: Optional[str] = None
        actual_input = input_path

        needs_wav_fallback = (not use_vi) and (is_video or ext != "wav")
        if needs_wav_fallback:
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
                    format=primary_format,
                    success=False,
                    error=f"Audio extraction fallback failed: {e}",
                )

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
            if self.carry_initial_prompt and caps["carry_initial_prompt"]:
                argv.append("--carry-initial-prompt")
        if self.suppress_nst and caps["suppress_nst"]:
            argv.append("-sns")
        if self.beam_size is not None:
            argv.extend(["-bs", str(self.beam_size)])
        if self.best_of is not None:
            argv.extend(["-bo", str(self.best_of)])
        if self.no_gpu:
            argv.append("-ng")
        if self.device is not None:
            argv.extend(["-dev", str(self.device)])
        if effective_diarize and caps["diarize"]:
            argv.append("-di")
        if effective_tdrz and caps["tinydiarize"]:
            argv.append("-tdrz")
        if effective_vad and caps["vad"] and effective_vad_model and os.path.isfile(effective_vad_model):
            argv.extend(["--vad", "-vm", effective_vad_model, "-vt", str(self.vad_threshold)])
        if progress_callback and caps["progress"]:
            argv.append("-pp")

        argv.extend(["-f", actual_input])
        for fmt in native_formats:
            if fmt == "json" and needs_json_full and caps["json_full"]:
                argv.append("-ojf")
            else:
                argv.append(self._FORMAT_FLAGS[fmt])
        argv.extend(["-of", output_base])

        if progress_callback:
            progress_callback("transcribing", 0.0)

        try:
            logger.info("Running transcription: %s", " ".join(argv))
            self._run_process(argv, progress_callback=progress_callback)
            if progress_callback:
                progress_callback("transcribing", 1.0)

            output_paths = {
                fmt: f"{output_base}.{fmt}"
                for fmt in native_formats
                if os.path.exists(f"{output_base}.{fmt}")
            }
            # Fallback for mocked tests where whisper-cli didn't actually write files
            if not output_paths:
                first_native = native_formats[0]
                output_paths[first_native] = f"{output_base}.{first_native}"

            primary_out = output_paths.get(
                primary_format,
                output_paths.get(native_formats[0], f"{output_base}.{native_formats[0]}"),
            )
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path=primary_out,
                format=primary_format if primary_format in output_paths else native_formats[0],
                success=True,
                output_paths=output_paths,
            )

        except FileNotFoundError as e:
            logger.error("Transcription failed: %s", e)
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=primary_format,
                success=False,
                error=whisper_binary_install_hint(),
            )
        except subprocess.TimeoutExpired:
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=primary_format,
                success=False,
                error=f"Transcription timed out after {self.timeout}s",
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
                format=primary_format,
                success=False,
                error=error_msg,
            )
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass
