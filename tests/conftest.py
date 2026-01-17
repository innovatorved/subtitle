"""
Pytest configuration and shared fixtures.

Provides common fixtures for testing the subtitle generator.
"""

import os
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_vtt_content():
    """Return sample VTT content."""
    return """WEBVTT

00:00:00.000 --> 00:00:03.500
Hello, this is a test subtitle.

00:00:04.000 --> 00:00:07.500
This is the second line of subtitles.

00:00:08.000 --> 00:00:12.000
And this is the third and final line.
"""


@pytest.fixture
def sample_srt_content():
    """Return sample SRT content."""
    return """1
00:00:00,000 --> 00:00:03,500
Hello, this is a test subtitle.

2
00:00:04,000 --> 00:00:07,500
This is the second line of subtitles.

3
00:00:08,000 --> 00:00:12,000
And this is the third and final line.
"""


@pytest.fixture
def temp_dir(tmp_path):
    """Return a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_model_manager(mocker):
    """Return a mocked ModelManager that doesn't download."""
    from src.models import ModelManager
    
    # Reset singleton for clean test
    ModelManager.reset_instance()
    
    manager = ModelManager(models_dir=str(mocker.tmp_path / "models"))
    
    # Mock download to avoid network calls
    mocker.patch.object(manager, "download_model", return_value="models/ggml-base.bin")
    
    yield manager
    
    # Reset after test
    ModelManager.reset_instance()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    from src.models.model_manager import ModelManager
    from src.config.config_loader import reset_config
    
    ModelManager.reset_instance()
    reset_config()
    
    yield
    
    ModelManager.reset_instance()
    reset_config()
