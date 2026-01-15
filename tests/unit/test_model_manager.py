"""
Unit tests for model manager.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.model_manager import ModelManager


class TestModelManager:
    """Tests for ModelManager singleton."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        ModelManager.reset_instance()
    
    def teardown_method(self):
        """Reset singleton after each test."""
        ModelManager.reset_instance()
    
    def test_singleton_instance(self):
        """Test that ModelManager is a singleton."""
        manager1 = ModelManager()
        manager2 = ModelManager()
        
        assert manager1 is manager2
    
    def test_singleton_with_different_args(self):
        """Test singleton behavior with different initialization args."""
        manager1 = ModelManager(models_dir="models1")
        manager2 = ModelManager(models_dir="models2")
        
        # Should return same instance
        assert manager1 is manager2
        # First initialization wins
        assert manager1.models_dir == "models1"
    
    def test_list_available_models(self):
        """Test listing available models."""
        manager = ModelManager()
        models = manager.list_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "base" in models
        assert "tiny" in models
        assert "small" in models
    
    def test_get_model_path(self):
        """Test model path generation."""
        manager = ModelManager()
        path = manager.get_model_path("base")
        
        assert "ggml-base.bin" in path
    
    def test_invalid_model_raises_error(self):
        """Test that invalid model name raises ValueError."""
        manager = ModelManager()
        
        with pytest.raises(ValueError):
            manager.get_model("invalid_model_name")
    
    def test_model_exists_false_for_missing(self):
        """Test model_exists returns False for missing model."""
        manager = ModelManager(models_dir="/tmp/test_models_nonexistent")
        
        assert manager.model_exists("base") is False
