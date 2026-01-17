"""
Custom exception hierarchy for the subtitle generator.

Provides specific exception types for different failure scenarios,
enabling better error handling and debugging.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class SubtitleError(Exception):
    """
    Base exception for all subtitle generator operations.
    
    All custom exceptions inherit from this class, allowing
    callers to catch all subtitle-related errors with a single handler.
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with contextual information
            cause: Optional original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        
        # Log the error with context
        log_message = f"{self.__class__.__name__}: {message}"
        if details:
            log_message += f" | Details: {details}"
        if cause:
            log_message += f" | Caused by: {cause}"
        logger.error(log_message)
    
    def __str__(self) -> str:
        result = self.message
        if self.details:
            result += f" (details: {self.details})"
        return result


class TranscriptionError(SubtitleError):
    """
    Raised when Whisper transcription fails.
    
    This can occur due to:
    - Invalid input file format
    - Whisper binary execution failure
    - Model loading issues
    - Audio processing errors
    """
    pass


class VideoProcessingError(SubtitleError):
    """
    Raised when video/FFmpeg operations fail.
    
    This can occur due to:
    - FFmpeg not installed or not in PATH
    - Unsupported video format
    - Corrupt video file
    - Insufficient disk space
    - Encoding/decoding errors
    """
    pass


class ModelError(SubtitleError):
    """
    Raised when model operations fail.
    
    This can occur due to:
    - Network errors during download
    - Invalid model name
    - Corrupt model file
    - Insufficient disk space
    - Permission errors
    """
    pass


class ValidationError(SubtitleError):
    """
    Raised when input validation fails.
    
    This can occur due to:
    - Invalid file path
    - Unsupported file format
    - Invalid model name
    - Invalid configuration values
    """
    pass


class ConfigurationError(SubtitleError):
    """
    Raised when configuration loading or parsing fails.
    
    This can occur due to:
    - Missing configuration file
    - Invalid YAML syntax
    - Missing required configuration values
    - Invalid configuration values
    """
    pass


class DownloadError(SubtitleError):
    """
    Raised when file download fails.
    
    This can occur due to:
    - Network connectivity issues
    - Invalid URL
    - Server errors
    - Timeout
    """
    pass


class BatchProcessingError(SubtitleError):
    """
    Raised when batch processing fails.
    
    This can occur due to:
    - Invalid input directory
    - No video files found
    - All files failed processing
    - State file corruption
    """
    pass


# Retry decorator for network operations
def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator that retries a function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch and retry
        
    Returns:
        Decorated function
    """
    import time
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
