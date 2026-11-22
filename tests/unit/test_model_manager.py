"""
Unit tests for model manager.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from subtitle_generator.models.model_manager import ModelManager


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

    def test_singleton_with_different_args(self, tmp_path):
        """Test per-directory caching: different models_dir returns distinct instances."""
        dir1 = str(tmp_path / "models1")
        dir2 = str(tmp_path / "models2")
        manager1 = ModelManager(models_dir=dir1)
        manager2 = ModelManager(models_dir=dir2)
        manager1_again = ModelManager(models_dir=dir1)

        assert manager1 is manager1_again
        assert manager1 is not manager2
        assert manager1.models_dir == dir1
        assert manager2.models_dir == dir2

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

    def test_alias_model_filenames(self):
        """Test that large, large-q5_0, and turbo map to v3/turbo filenames."""
        manager = ModelManager()
        assert manager.get_model_path("large").endswith("ggml-large-v3.bin")
        assert manager.get_model_path("large-q5_0").endswith("ggml-large-v3-q5_0.bin")
        assert manager.get_model_path("turbo").endswith("ggml-large-v3-turbo.bin")
        assert manager.get_model_path("large-v3-turbo").endswith("ggml-large-v3-turbo.bin")

    def test_atomic_download_cleans_up_part_file_on_error(self, tmp_path):
        """Test that failed download does not leave corrupt final file."""
        manager = ModelManager(models_dir=str(tmp_path))
        output_path = str(tmp_path / "ggml-base.bin")

        with patch("urllib.request.urlopen", side_effect=OSError("network dropped")):
            with pytest.raises(OSError):
                manager._download_file("https://example.com/ggml-base.bin", output_path)

        assert not os.path.exists(output_path)

    def test_atomic_download_replaces_target_on_success(self, tmp_path):
        """Test that successful download writes via .part and atomically replaces output_path."""
        import io

        manager = ModelManager(models_dir=str(tmp_path))
        output_path = str(tmp_path / "ggml-base.bin")

        class FakeResp(io.BytesIO):
            status = 200
            headers = {"Content-Length": "17"}
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        with patch("urllib.request.urlopen", return_value=FakeResp(b"valid-model-bytes")):
            manager._download_file("https://example.com/ggml-base.bin", output_path)

        assert os.path.exists(output_path)
        assert not os.path.exists(f"{output_path}.part")
        with open(output_path, "rb") as f:
            assert f.read() == b"valid-model-bytes"
