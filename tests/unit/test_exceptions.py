"""
Unit tests for exceptions module.
"""

import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.exceptions import (
    SubtitleError,
    TranscriptionError,
    VideoProcessingError,
    ModelError,
    ValidationError,
    ConfigurationError,
    DownloadError,
    retry_on_error,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""
    
    def test_subtitle_error_base(self):
        """Test SubtitleError is the base."""
        error = SubtitleError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
    
    def test_transcription_error_inherits(self):
        """Test TranscriptionError inherits from SubtitleError."""
        error = TranscriptionError("transcription failed")
        assert isinstance(error, SubtitleError)
        assert isinstance(error, Exception)
    
    def test_video_processing_error_inherits(self):
        """Test VideoProcessingError inherits from SubtitleError."""
        error = VideoProcessingError("ffmpeg failed")
        assert isinstance(error, SubtitleError)
    
    def test_model_error_inherits(self):
        """Test ModelError inherits from SubtitleError."""
        error = ModelError("model not found")
        assert isinstance(error, SubtitleError)
    
    def test_validation_error_inherits(self):
        """Test ValidationError inherits from SubtitleError."""
        error = ValidationError("invalid input")
        assert isinstance(error, SubtitleError)


class TestExceptionDetails:
    """Tests for exception details and context."""
    
    def test_error_with_details(self):
        """Test error with details dictionary."""
        error = SubtitleError(
            "operation failed",
            details={"file": "test.mp4", "code": 123}
        )
        
        assert error.message == "operation failed"
        assert error.details["file"] == "test.mp4"
        assert error.details["code"] == 123
    
    def test_error_with_cause(self):
        """Test error with cause exception."""
        original = ValueError("original error")
        error = SubtitleError("wrapped error", cause=original)
        
        assert error.cause is original
    
    def test_str_includes_details(self):
        """Test __str__ includes details."""
        error = SubtitleError(
            "test",
            details={"key": "value"}
        )
        
        result = str(error)
        assert "test" in result
        assert "key" in result


class TestRetryDecorator:
    """Tests for retry_on_error decorator."""
    
    def test_retry_succeeds_first_try(self):
        """Test function succeeds on first try."""
        call_count = [0]
        
        @retry_on_error(max_attempts=3, delay=0.01)
        def always_succeeds():
            call_count[0] += 1
            return "success"
        
        result = always_succeeds()
        
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retry_succeeds_after_failures(self):
        """Test function succeeds after initial failures."""
        call_count = [0]
        
        @retry_on_error(max_attempts=3, delay=0.01)
        def succeeds_on_third():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")
            return "success"
        
        result = succeeds_on_third()
        
        assert result == "success"
        assert call_count[0] == 3
    
    def test_retry_exhausted(self):
        """Test exception is raised after all retries exhausted."""
        call_count = [0]
        
        @retry_on_error(max_attempts=2, delay=0.01)
        def always_fails():
            call_count[0] += 1
            raise ValueError("always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count[0] == 2
