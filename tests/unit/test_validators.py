"""
Unit tests for validators.
"""

import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.validators import (
    validate_video_path,
    validate_audio_path,
    validate_media_path,
    validate_model_name,
    validate_output_format,
    get_available_models,
    get_supported_formats,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


class TestValidateVideoPath:
    """Tests for video path validation."""
    
    def test_empty_path(self):
        """Test empty path returns invalid."""
        valid, error = validate_video_path("")
        assert valid is False
        assert "empty" in error.lower()
    
    def test_unsupported_extension(self):
        """Test unsupported extension returns invalid."""
        valid, error = validate_video_path("file.xyz", must_exist=False)
        assert valid is False
        assert "unsupported" in error.lower()
    
    def test_valid_extension(self):
        """Test valid extension with must_exist=False."""
        valid, error = validate_video_path("video.mp4", must_exist=False)
        assert valid is True
        assert error is None
    
    def test_nonexistent_file(self):
        """Test non-existent file with must_exist=True."""
        valid, error = validate_video_path("/nonexistent/video.mp4", must_exist=True)
        assert valid is False
        assert "not found" in error.lower()


class TestValidateModelName:
    """Tests for model name validation."""
    
    def test_empty_model(self):
        """Test empty model name returns invalid."""
        valid, error = validate_model_name("")
        assert valid is False
        assert "empty" in error.lower()
    
    def test_invalid_model(self):
        """Test invalid model name returns invalid."""
        valid, error = validate_model_name("nonexistent_model")
        assert valid is False
        assert "unknown" in error.lower()
    
    def test_valid_model(self):
        """Test valid model name returns valid."""
        valid, error = validate_model_name("base")
        assert valid is True
        assert error is None
    
    def test_valid_models_list(self):
        """Test all models in list are considered valid."""
        for model in get_available_models():
            valid, _ = validate_model_name(model)
            assert valid is True


class TestValidateOutputFormat:
    """Tests for output format validation."""
    
    def test_empty_format(self):
        """Test empty format returns invalid."""
        valid, error = validate_output_format("")
        assert valid is False
    
    def test_invalid_format(self):
        """Test invalid format returns invalid."""
        valid, error = validate_output_format("xyz")
        assert valid is False
    
    def test_valid_format(self):
        """Test valid format returns valid."""
        valid, error = validate_output_format("vtt")
        assert valid is True
        
        valid, error = validate_output_format("srt")
        assert valid is True


class TestGetters:
    """Tests for getter functions."""
    
    def test_get_available_models(self):
        """Test getting available models."""
        models = get_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "base" in models
        assert "tiny" in models
    
    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = get_supported_formats()
        
        assert isinstance(formats, list)
        assert "vtt" in formats
        assert "srt" in formats
