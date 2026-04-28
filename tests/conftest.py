"""Shared pytest fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_vtt_content():
    return (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:03.500\nHello, this is a test subtitle.\n\n"
        "00:00:04.000 --> 00:00:07.500\nThis is the second line of subtitles.\n\n"
        "00:00:08.000 --> 00:00:12.000\nAnd this is the third and final line.\n"
    )


@pytest.fixture
def sample_srt_content():
    return (
        "1\n00:00:00,000 --> 00:00:03,500\nHello, this is a test subtitle.\n\n"
        "2\n00:00:04,000 --> 00:00:07,500\nThis is the second line of subtitles.\n\n"
        "3\n00:00:08,000 --> 00:00:12,000\nAnd this is the third and final line.\n"
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    from subtitle_generator.models.model_manager import ModelManager

    ModelManager.reset_instance()
    yield
    ModelManager.reset_instance()
