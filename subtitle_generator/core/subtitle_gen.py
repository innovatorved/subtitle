"""Subtitle generation orchestration."""

import logging
import os
import shutil
from typing import Callable, Optional

from .transcriber import TranscriberStrategy, TranscriptionResult
from ..models import ModelManager
from ..utils.file_handler import file_exists

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """Coordinates model resolution and transcription."""

    def __init__(
        self,
        transcriber: TranscriberStrategy,
        model_manager: Optional[ModelManager] = None,
    ):
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
        if not file_exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback("preparing", 0.0)

        try:
            model_path = self.model_manager.get_model(model_name)
            logger.info(f"Using model: {model_path}")
        except Exception as e:
            raise ValueError(f"Failed to get model '{model_name}': {e}")

        if progress_callback:
            progress_callback("preparing", 1.0)

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
        output_dir: str = "data",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> tuple[str, bool]:
        """Generate subtitles and move output to ``output_path``
        (or next to the input video if ``output_path`` is None).
        """
        result = self.generate(
            input_path=input_path,
            model_name=model_name,
            output_format=output_format,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        if not result.success:
            return ("", False)

        if output_path:
            final_output_path = output_path
        else:
            base, _ = os.path.splitext(input_path)
            final_output_path = f"{base}.{output_format}"

        try:
            if os.path.exists(result.output_path):
                final_dir = os.path.dirname(final_output_path)
                if final_dir:
                    os.makedirs(final_dir, exist_ok=True)
                if os.path.isfile(final_output_path):
                    os.remove(final_output_path)
                # shutil.move handles cross-filesystem moves; os.rename
                # would raise EXDEV when /tmp is on a separate device.
                shutil.move(result.output_path, final_output_path)
                logger.info(f"Renamed output to: {final_output_path}")
                return (final_output_path, True)
        except OSError as e:
            logger.error(f"Failed to rename output: {e}")
            return (result.output_path, True)

        return (result.output_path, True)
