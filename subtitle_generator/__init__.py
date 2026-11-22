"""Subtitle Generator v4.0.0 — industry-standard AI subtitle toolkit."""

__version__ = "4.1.0"

from .core import (
    BatchProcessor,
    CloudTranscriber,
    FasterWhisperTranscriber,
    FolderWatcher,
    SubtitleGenerator,
    VideoProcessor,
    WhisperCppTranscriber,
    create_transcriber,
)
from .models import ModelManager
from .utils.doctor import format_diagnostics, run_diagnostics
from .utils.formatters import (
    ASSFormatter,
    JSONFormatter,
    TTMLFormatter,
    convert_subtitle_file,
    convert_subtitle_format,
)
from .utils.postprocess import (
    lint_segments,
    lint_subtitle_file,
    reflow_segments,
    scrub_hallucinations,
    shift_segments,
    shift_subtitle_file,
)
from .utils.translator import translate_segments, translate_subtitle_file

__all__ = [
    "__version__",
    "ASSFormatter",
    "BatchProcessor",
    "CloudTranscriber",
    "FasterWhisperTranscriber",
    "FolderWatcher",
    "JSONFormatter",
    "ModelManager",
    "SubtitleGenerator",
    "TTMLFormatter",
    "VideoProcessor",
    "WhisperCppTranscriber",
    "convert_subtitle_file",
    "convert_subtitle_format",
    "create_transcriber",
    "format_diagnostics",
    "lint_segments",
    "lint_subtitle_file",
    "reflow_segments",
    "run_diagnostics",
    "scrub_hallucinations",
    "shift_segments",
    "shift_subtitle_file",
    "translate_segments",
    "translate_subtitle_file",
]
