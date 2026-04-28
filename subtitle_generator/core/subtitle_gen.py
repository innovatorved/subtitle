"""
Subtitle generation orchestration module.

This module coordinates the transcription and subtitle generation process,
using the transcriber strategy and handling the overall workflow.
"""

import logging
import os
from typing import Optional, Callable

from .transcriber import TranscriberStrategy, TranscriptionResult
from ..models import ModelManager
from ..utils.file_handler import file_exists, sanitize_filename

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """
    Orchestrates the subtitle generation process.
    
    Uses a transcriber strategy to generate subtitles from video/audio files.
    """
    
    def __init__(
        self,
        transcriber: TranscriberStrategy,
        model_manager: Optional[ModelManager] = None,
    ):
        """
        Initialize the subtitle generator.
        
        Args:
            transcriber: The transcription strategy to use
            model_manager: Optional model manager (uses singleton if not provided)
        """
        self.transcriber = transcriber
        self.model_manager = model_manager or ModelManager()
    
    def generate(
        self,
        input_path: str,
        model_name: str = "base",
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> TranscriptionResult:
        """
        Generate subtitles for the given input file.
        
        Args:
            input_path: Path to input audio/video file
            model_name: Name of the model to use (e.g., 'base', 'tiny', 'small')
            output_format: Output subtitle format (vtt, srt, etc.)
            output_dir: Directory to write output files
            progress_callback: Optional callback for progress updates
            
        Returns:
            TranscriptionResult with generation details
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If model is invalid or not available
        """
        # Validate input file
        if not file_exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Notify progress
        if progress_callback:
            progress_callback("preparing", 0.0)
        
        # Get model path (downloads if necessary)
        try:
            model_path = self.model_manager.get_model(model_name)
            logger.info(f"Using model: {model_path}")
        except Exception as e:
            raise ValueError(f"Failed to get model '{model_name}': {e}")
        
        if progress_callback:
            progress_callback("preparing", 1.0)
        
        # Run transcription
        result = self.transcriber.transcribe(
            input_path=input_path,
            model_path=model_path,
            output_format=output_format,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )
        
        if not result.success:
            logger.error(f"Transcription failed: {result.error}")
        else:
            logger.info(f"Subtitles generated: {result.output_path}")
        
        return result
    
    def generate_and_rename(
        self,
        input_path: str,
        model_name: str = "base",
        output_format: str = "vtt",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> tuple[str, bool]:
        """
        Generate subtitles and rename output to match input filename.
        
        Args:
            input_path: Path to input audio/video file
            model_name: Name of the model to use
            output_format: Output subtitle format
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (output_path, success)
        """
        result = self.generate(
            input_path=input_path,
            model_name=model_name,
            output_format=output_format,
            progress_callback=progress_callback,
        )
        
        if not result.success:
            return ("", False)
        
        # Rename to match input file
        base, _ = os.path.splitext(input_path)
        final_output_path = f"{base}.{output_format}"
        
        try:
            if os.path.exists(result.output_path):
                os.rename(result.output_path, final_output_path)
                logger.info(f"Renamed output to: {final_output_path}")
                return (final_output_path, True)
        except OSError as e:
            logger.error(f"Failed to rename output: {e}")
            return (result.output_path, True)
        
        return (result.output_path, True)
