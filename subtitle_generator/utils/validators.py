"""
Input validation utilities.

Provides functions for validating various inputs like file paths,
model names, and output formats.
"""

import os
import logging
from typing import Optional

from .file_handler import file_exists, get_file_extension

logger = logging.getLogger(__name__)

# Supported video extensions
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpeg", "mpg"
}

# Supported audio extensions
AUDIO_EXTENSIONS = {
    "mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"
}

# All supported media extensions
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Available Whisper models
AVAILABLE_MODELS = [
    "tiny.en",
    "tiny",
    "tiny-q5_1",
    "tiny.en-q5_1",
    "base.en",
    "base",
    "base-q5_1",
    "base.en-q5_1",
    "small.en",
    "small.en-tdrz",
    "small",
    "small-q5_1",
    "small.en-q5_1",
    "medium",
    "medium.en",
    "medium-q5_0",
    "medium.en-q5_0",
    "large-v1",
    "large-v2",
    "large",
    "large-q5_0",
]

# Supported subtitle formats
SUBTITLE_FORMATS = {"vtt", "srt", "txt", "json", "lrc"}


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_video_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate a video file path.
    
    Args:
        path: Path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return (False, "Video path cannot be empty")
    
    # Check extension
    ext = get_file_extension(path)
    if ext not in VIDEO_EXTENSIONS:
        return (False, f"Unsupported video format: .{ext}. Supported: {VIDEO_EXTENSIONS}")
    
    # Check existence if required
    if must_exist and not file_exists(path):
        return (False, f"Video file not found: {path}")
    
    return (True, None)


def validate_audio_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate an audio file path.
    
    Args:
        path: Path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return (False, "Audio path cannot be empty")
    
    ext = get_file_extension(path)
    if ext not in AUDIO_EXTENSIONS:
        return (False, f"Unsupported audio format: .{ext}. Supported: {AUDIO_EXTENSIONS}")
    
    if must_exist and not file_exists(path):
        return (False, f"Audio file not found: {path}")
    
    return (True, None)


def validate_media_path(path: str, must_exist: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate an audio or video file path.
    
    Args:
        path: Path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return (False, "Media path cannot be empty")
    
    ext = get_file_extension(path)
    if ext not in MEDIA_EXTENSIONS:
        return (False, f"Unsupported media format: .{ext}. Supported: {MEDIA_EXTENSIONS}")
    
    if must_exist and not file_exists(path):
        return (False, f"Media file not found: {path}")
    
    return (True, None)


def validate_model_name(model_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate a Whisper model name.
    
    Args:
        model_name: Model name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not model_name:
        return (False, "Model name cannot be empty")
    
    if model_name not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS)
        return (False, f"Unknown model: {model_name}. Available: {available}")
    
    return (True, None)


def validate_output_format(format_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate a subtitle output format.
    
    Args:
        format_name: Format name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not format_name:
        return (False, "Format cannot be empty")
    
    format_lower = format_name.lower()
    if format_lower not in SUBTITLE_FORMATS:
        available = ", ".join(SUBTITLE_FORMATS)
        return (False, f"Unknown format: {format_name}. Available: {available}")
    
    return (True, None)


def validate_output_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate an output file path.
    
    Args:
        path: Path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return (False, "Output path cannot be empty")
    
    # Check if parent directory exists or can be created
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            return (False, f"Cannot create output directory: {e}")
    
    return (True, None)


def get_available_models() -> list[str]:
    """
    Get list of available model names.
    
    Returns:
        List of available model names
    """
    return AVAILABLE_MODELS.copy()


def get_supported_formats() -> list[str]:
    """
    Get list of supported subtitle formats.
    
    Returns:
        List of supported format names
    """
    return list(SUBTITLE_FORMATS)
