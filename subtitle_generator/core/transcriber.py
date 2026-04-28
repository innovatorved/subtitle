"""
Transcriber module with Strategy pattern for different transcription engines.

This module provides an abstract interface for transcription engines,
allowing easy swapping between different implementations (Whisper.cpp, etc.)
"""

import logging
import os
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable

from ..utils.exceptions import TranscriptionError
from ..utils.paths import (
    find_whisper_binary,
    whisper_binary_install_hint,
)

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""

    process_id: str
    input_path: str
    output_path: str
    format: str
    success: bool
    error: Optional[str] = None


class TranscriberStrategy(ABC):
    """Abstract base class for transcription strategies."""

    @abstractmethod
    def transcribe(
        self,
        input_path: str,
        model_path: str,
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio/video file to subtitles.

        Args:
            input_path: Path to input audio/video file
            model_path: Path to the model file
            output_format: Output subtitle format (vtt, srt, etc.)
            output_dir: Directory to write output files
            progress_callback: Optional callback for progress updates

        Returns:
            TranscriptionResult with transcription details
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        pass


class WhisperCppTranscriber(TranscriberStrategy):
    """Whisper.cpp binary-based transcription implementation."""

    # Map subtitle format to whisper.cpp output flag.
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
        """
        Initialize Whisper.cpp transcriber.

        Args:
            binary_path: Optional explicit path to the whisper-cli binary.
                When ``None`` (the default), the binary is discovered at
                instantiation time via :func:`utils.paths.find_whisper_binary`,
                which checks the ``SUBTITLE_WHISPER_BINARY`` env var, ``PATH``,
                and the legacy ``./binary/whisper-cli`` checkout layout.
            threads: Number of threads to use
            processors: Number of processors to use

        Raises:
            TranscriptionError: If the whisper-cli binary cannot be located.
                The error includes OS-specific install instructions so the
                user can fix it without reading source code.
        """
        resolved = find_whisper_binary(binary_path)
        if not resolved:
            raise TranscriptionError(
                whisper_binary_install_hint(),
                details={
                    "explicit_binary_path": binary_path,
                    "cwd": os.getcwd(),
                },
            )
        self.binary_path = resolved
        self.threads = threads
        self.processors = processors
        logger.debug("Using whisper-cli binary at: %s", self.binary_path)

    def get_supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        return list(self._FORMAT_FLAGS.keys())

    def transcribe(
        self,
        input_path: str,
        model_path: str,
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> TranscriptionResult:
        """
        Transcribe using Whisper.cpp binary.

        Args:
            input_path: Path to input audio/video file
            model_path: Path to the model file
            output_format: Output subtitle format
            output_dir: Directory to write output files
            progress_callback: Optional callback for progress updates

        Returns:
            TranscriptionResult with transcription details
        """
        process_id = str(uuid.uuid4())

        os.makedirs(output_dir, exist_ok=True)

        # whisper.cpp appends the format extension itself, so pass a
        # base path without one.
        output_base = os.path.join(output_dir, process_id)

        output_flag = self._FORMAT_FLAGS.get(output_format, "-ovtt")
        actual_format = output_format if output_format in self._FORMAT_FLAGS else "vtt"

        # Use an argv list rather than `shell=True`. This eliminates a class
        # of injection / quoting bugs on filenames containing spaces, quotes,
        # or shell metacharacters (the previous f-string version broke on
        # those) and complies with the project's secure-shell-execution rule.
        argv = [
            self.binary_path,
            "-t",
            str(self.threads),
            "-p",
            str(self.processors),
            "-m",
            model_path,
            "-vi",  # video input mode
            "-f",
            input_path,
            output_flag,
            "-of",
            output_base,
        ]

        if progress_callback:
            progress_callback("transcribing", 0.0)

        try:
            logger.info("Running transcription: %s", " ".join(argv))
            completed = subprocess.run(
                argv,
                check=True,
                capture_output=True,
            )
            if completed.stdout:
                logger.debug(
                    "Transcription stdout: %s",
                    completed.stdout.decode("utf-8", errors="replace"),
                )

            if progress_callback:
                progress_callback("transcribing", 1.0)

            output_path = f"{output_base}.{actual_format}"

            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path=output_path,
                format=actual_format,
                success=True,
            )

        except FileNotFoundError as e:
            # The binary path was valid at construction time but disappeared
            # between then and now (e.g. user uninstalled). Surface the same
            # actionable hint.
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
