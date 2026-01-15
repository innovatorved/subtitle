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
    
    def __init__(
        self,
        binary_path: str = "./binary/whisper-cli",
        threads: int = 4,
        processors: int = 1,
    ):
        """
        Initialize Whisper.cpp transcriber.
        
        Args:
            binary_path: Path to whisper-cli binary
            threads: Number of threads to use
            processors: Number of processors to use
        """
        self.binary_path = binary_path
        self.threads = threads
        self.processors = processors
    
    def get_supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        return ["vtt", "srt", "txt", "json", "lrc"]
    
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
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Build output path (without extension - whisper adds it)
        output_base = os.path.join(output_dir, process_id)
        
        # Map format to whisper.cpp output flag
        format_flags = {
            "vtt": "-ovtt",
            "srt": "-osrt",
            "txt": "-otxt",
            "json": "-oj",
            "lrc": "-olrc",
        }
        
        output_flag = format_flags.get(output_format, "-ovtt")
        actual_format = output_format if output_format in format_flags else "vtt"
        
        # Build command
        command = (
            f"{self.binary_path} "
            f"-t {self.threads} "
            f"-p {self.processors} "
            f"-m {model_path} "
            f"-vi "  # Video input mode
            f"-f {input_path} "
            f"{output_flag} "
            f"-of {output_base}"
        )
        
        if progress_callback:
            progress_callback("transcribing", 0.0)
        
        try:
            logger.info(f"Running transcription: {command}")
            result = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT
            )
            logger.debug(f"Transcription output: {result.decode('utf-8')}")
            
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
            
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode("utf-8").strip() if e.output else str(e)
            logger.error(f"Transcription failed: {error_msg}")
            
            return TranscriptionResult(
                process_id=process_id,
                input_path=input_path,
                output_path="",
                format=actual_format,
                success=False,
                error=error_msg,
            )
