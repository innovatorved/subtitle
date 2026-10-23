"""Subtitle Generator - generate subtitles for video/audio using whisper.cpp."""

__version__ = "3.2.0"

from .core import BatchProcessor, SubtitleGenerator, VideoProcessor, WhisperCppTranscriber
from .models import ModelManager
from .utils.formatters import convert_subtitle_file, convert_subtitle_format

__all__ = [
    "__version__",
    "BatchProcessor",
    "ModelManager",
    "SubtitleGenerator",
    "VideoProcessor",
    "WhisperCppTranscriber",
    "convert_subtitle_file",
    "convert_subtitle_format",
]
