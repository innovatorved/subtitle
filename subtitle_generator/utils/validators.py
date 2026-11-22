"""Input validation utilities for paths, models, formats, and presets."""

from __future__ import annotations

import logging
import os
from typing import Optional

from ..models.model_manager import ModelManager
from .file_handler import file_exists, get_file_extension

logger = logging.getLogger(__name__)

# Supported video extensions
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpeg", "mpg", "ts",
}

# Supported audio extensions
AUDIO_EXTENSIONS = {
    "mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus",
}

# All supported media extensions
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Available Whisper models (single source of truth in ModelManager)
AVAILABLE_MODELS = ModelManager.MODELS

# Supported subtitle formats
SUBTITLE_FORMATS = {"vtt", "srt", "ass", "ttml", "txt", "json", "lrc", "csv"}

# Supported subtitle presets
SUBTITLE_PRESETS = {"netflix", "netflix-kids", "bbc", "reels", "shorts"}


def validate_video_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    if not path:
        return (False, "Video path cannot be empty")
    ext = get_file_extension(path)
    if ext not in VIDEO_EXTENSIONS:
        return (False, f"Unsupported video format: .{ext}. Supported: {VIDEO_EXTENSIONS}")
    if must_exist and not file_exists(path):
        return (False, f"Video file not found: {path}")
    return (True, None)


def validate_audio_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    if not path:
        return (False, "Audio path cannot be empty")
    ext = get_file_extension(path)
    if ext not in AUDIO_EXTENSIONS:
        return (False, f"Unsupported audio format: .{ext}. Supported: {AUDIO_EXTENSIONS}")
    if must_exist and not file_exists(path):
        return (False, f"Audio file not found: {path}")
    return (True, None)


def validate_media_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    if not path:
        return (False, "Media path cannot be empty")
    ext = get_file_extension(path)
    if ext not in MEDIA_EXTENSIONS:
        return (False, f"Unsupported media format: .{ext}. Supported: {MEDIA_EXTENSIONS}")
    if must_exist and not file_exists(path):
        return (False, f"Media file not found: {path}")
    return (True, None)


def validate_model_name(model_name: str) -> tuple[bool, Optional[str]]:
    if not model_name:
        return (False, "Model name cannot be empty")
    if model_name not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS)
        return (False, f"Unknown model: {model_name}. Available: {available}")
    return (True, None)


def validate_output_format(format_name: str) -> tuple[bool, Optional[str]]:
    if not format_name:
        return (False, "Format cannot be empty")
    format_lower = format_name.strip().lower()
    if format_lower not in SUBTITLE_FORMATS:
        available = ", ".join(sorted(SUBTITLE_FORMATS))
        return (False, f"Unknown format: {format_name}. Available: {available}")
    return (True, None)


def parse_output_formats(formats_spec: str) -> tuple[list[str], Optional[str]]:
    """Parse and validate a comma-separated format list (e.g. ``'srt,vtt,ass'``)."""
    if not formats_spec or not formats_spec.strip():
        return ([], "Format cannot be empty")
    parts = [p.strip().lower() for p in formats_spec.split(",") if p.strip()]
    if not parts:
        return ([], "Format cannot be empty")
    deduped: list[str] = []
    for fmt in parts:
        ok, err = validate_output_format(fmt)
        if not ok:
            return ([], err)
        if fmt not in deduped:
            deduped.append(fmt)
    return (deduped, None)


def validate_output_path(path: str) -> tuple[bool, Optional[str]]:
    if not path:
        return (False, "Output path cannot be empty")
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            return (False, f"Cannot create output directory: {e}")
    return (True, None)


def get_available_models() -> list[str]:
    return AVAILABLE_MODELS.copy()


def get_supported_formats() -> list[str]:
    return sorted(SUBTITLE_FORMATS)
