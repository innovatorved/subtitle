"""
File handling utilities.

Provides functions for common file operations like existence checks,
directory creation, and filename sanitization.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists at the given path.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file exists, False otherwise
    """
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path)
    except Exception as e:
        logger.error(f"Error checking file existence: {e}")
        return False


def directory_exists(dir_path: str) -> bool:
    """
    Check if a directory exists at the given path.
    
    Args:
        dir_path: Path to the directory to check
        
    Returns:
        True if directory exists, False otherwise
    """
    try:
        return os.path.exists(dir_path) and os.path.isdir(dir_path)
    except Exception as e:
        logger.error(f"Error checking directory existence: {e}")
        return False


def ensure_directory(dir_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to the directory to ensure exists
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename by replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        replacement: Character to replace invalid chars with
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Replace spaces with replacement char
    sanitized = filename.replace(" ", replacement)
    
    # Remove or replace characters that are problematic on various filesystems
    # Keep only alphanumeric, underscores, hyphens, and dots
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', replacement, sanitized)
    
    # Remove leading/trailing spaces and dots (Windows issue)
    sanitized = sanitized.strip(". ")
    
    # Collapse multiple replacement chars
    sanitized = re.sub(f'{re.escape(replacement)}+', replacement, sanitized)
    
    return sanitized


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension (without the dot).
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension without the leading dot, lowercase
    """
    _, ext = os.path.splitext(file_path)
    return ext.lstrip(".").lower()


def get_file_basename(file_path: str, include_extension: bool = False) -> str:
    """
    Get the base name of a file.
    
    Args:
        file_path: Path to the file
        include_extension: Whether to include the file extension
        
    Returns:
        Base name of the file
    """
    basename = os.path.basename(file_path)
    if not include_extension:
        basename, _ = os.path.splitext(basename)
    return basename


def get_output_path(
    input_path: str,
    suffix: str = "_output",
    new_extension: Optional[str] = None,
) -> str:
    """
    Generate an output path based on input path.
    
    Args:
        input_path: Original input file path
        suffix: Suffix to add before extension
        new_extension: Optional new extension (without dot)
        
    Returns:
        Generated output path
    """
    base, ext = os.path.splitext(input_path)
    if new_extension:
        ext = f".{new_extension.lstrip('.')}"
    return f"{base}{suffix}{ext}"


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes, or -1 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return -1


def list_files_with_extension(
    directory: str,
    extension: str,
    recursive: bool = False,
) -> list[str]:
    """
    List all files with a given extension in a directory.
    
    Args:
        directory: Directory to search
        extension: File extension to match (without dot)
        recursive: Whether to search subdirectories
        
    Returns:
        List of file paths matching the extension
    """
    extension = extension.lstrip(".")
    pattern = f"**/*.{extension}" if recursive else f"*.{extension}"
    
    path = Path(directory)
    return [str(f) for f in path.glob(pattern) if f.is_file()]
