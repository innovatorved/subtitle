"""Utilities module - File handling, downloads, validation, formatting, QC, config."""

from .config import get_config_default, load_config, write_default_config
from .doctor import format_diagnostics, run_diagnostics
from .downloader import download_file, is_url
from .exceptions import (
    BatchProcessingError,
    ConfigurationError,
    DownloadError,
    ModelError,
    SubtitleError,
    TranscriptionError,
    ValidationError,
    VideoProcessingError,
    retry_on_error,
)
from .file_handler import ensure_directory, file_exists, sanitize_filename
from .formatters import (
    ASSFormatter,
    JSONFormatter,
    SRTFormatter,
    SubtitleFormatterFactory,
    TTMLFormatter,
    VTTFormatter,
)
from .postprocess import (
    lint_segments,
    lint_subtitle_file,
    reflow_segments,
    scrub_hallucinations,
    shift_segments,
    shift_subtitle_file,
)
from .translator import translate_segments, translate_subtitle_file
from .validators import validate_model_name, validate_video_path

__all__ = [
    "file_exists",
    "ensure_directory",
    "sanitize_filename",
    "is_url",
    "download_file",
    "validate_video_path",
    "validate_model_name",
    "SubtitleFormatterFactory",
    "VTTFormatter",
    "SRTFormatter",
    "ASSFormatter",
    "TTMLFormatter",
    "JSONFormatter",
    "SubtitleError",
    "TranscriptionError",
    "VideoProcessingError",
    "ModelError",
    "ValidationError",
    "ConfigurationError",
    "DownloadError",
    "BatchProcessingError",
    "retry_on_error",
    "load_config",
    "get_config_default",
    "write_default_config",
    "run_diagnostics",
    "format_diagnostics",
    "reflow_segments",
    "scrub_hallucinations",
    "shift_segments",
    "shift_subtitle_file",
    "lint_segments",
    "lint_subtitle_file",
    "translate_segments",
    "translate_subtitle_file",
]
