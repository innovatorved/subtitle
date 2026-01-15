"""
Unit tests for configuration module.
"""

import os
import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.settings import Settings, WhisperSettings, PathSettings
from src.config.config_loader import load_config, _deep_merge, reset_config


class TestSettings:
    """Tests for Settings dataclass."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.whisper.default_model == "base"
        assert settings.whisper.threads == 4
        assert settings.formats.default == "vtt"
    
    def test_from_dict(self):
        """Test creating settings from dictionary."""
        data = {
            "whisper": {
                "default_model": "small",
                "threads": 8,
            },
            "formats": {
                "default": "srt",
            },
        }
        
        settings = Settings.from_dict(data)
        
        assert settings.whisper.default_model == "small"
        assert settings.whisper.threads == 8
        assert settings.formats.default == "srt"
    
    def test_to_dict(self):
        """Test converting settings to dictionary."""
        settings = Settings()
        data = settings.to_dict()
        
        assert "whisper" in data
        assert "formats" in data
        assert data["whisper"]["default_model"] == "base"


class TestDeepMerge:
    """Tests for deep merge function."""
    
    def test_simple_merge(self):
        """Test simple dictionary merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        
        result = _deep_merge(base, override)
        
        assert result["a"] == 1
        assert result["b"] == 3
        assert result["c"] == 4
    
    def test_nested_merge(self):
        """Test nested dictionary merge."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        
        result = _deep_merge(base, override)
        
        assert result["outer"]["a"] == 1
        assert result["outer"]["b"] == 3
        assert result["outer"]["c"] == 4


class TestConfigLoader:
    """Tests for config loader."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        reset_config()
        settings = load_config()
        
        assert settings is not None
        assert isinstance(settings, Settings)
    
    def test_load_custom_config(self, tmp_path):
        """Test loading custom configuration file."""
        import yaml
        
        config_path = tmp_path / "custom.yaml"
        config_data = {
            "whisper": {
                "default_model": "tiny",
                "threads": 2,
            },
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        reset_config()
        settings = load_config(config_path=str(config_path))
        
        assert settings.whisper.default_model == "tiny"
        assert settings.whisper.threads == 2
