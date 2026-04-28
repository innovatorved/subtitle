"""Transcriber strategy and the whisper.cpp implementation."""

import logging
import os
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

from ..utils.exceptions import TranscriptionError
from ..utils.paths import find_whisper_binary, whisper_binary_install_hint

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
    }

    def __init__(
        self,
        binary_path: Optional[str] = None,
        threads: int = 4,
        processors: int = 1,
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

    def get_supported_formats(self) -> list[str]:
        return list(self._FORMAT_FLAGS.keys())

    def transcribe(
        self,
        input_path: str,
        model_path: str,
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> TranscriptionResult:
        process_id = str(uuid.uuid4())
        os.makedirs(output_dir, exist_ok=True)
        output_base = os.path.join(output_dir, process_id)

        output_flag = self._FORMAT_FLAGS.get(output_format, "-ovtt")
        actual_format = output_format if output_format in self._FORMAT_FLAGS else "vtt"

        # argv list (no shell=True): handles spaces/quotes in filenames safely.
        argv = [
            self.binary_path,
            "-t", str(self.threads),
            "-p", str(self.processors),
            "-m", model_path,
            "-vi",
            "-f", input_path,
            output_flag,
            "-of", output_base,
        ]

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
