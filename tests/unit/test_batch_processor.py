"""
Unit tests for batch processor.
"""

import json
import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.batch_processor import (
    BatchProcessor,
    BatchState,
    BatchFileResult,
    BatchSummary,
    DEFAULT_VIDEO_EXTENSIONS,
)


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_init_default_values(self):
        """Test default initialization values."""
        processor = BatchProcessor()
        
        assert processor.workers == 4
        assert processor.model == "base"
        assert processor.output_format == "vtt"
        assert processor.extensions == DEFAULT_VIDEO_EXTENSIONS

    def test_init_custom_values(self):
        """Test custom initialization values."""
        processor = BatchProcessor(
            workers=8,
            model="small",
            output_format="srt",
            extensions=["mp4", "mkv"],
        )
        
        assert processor.workers == 8
        assert processor.model == "small"
        assert processor.output_format == "srt"
        assert processor.extensions == ["mp4", "mkv"]

    def test_workers_minimum(self):
        """Test that workers is at least 1."""
        processor = BatchProcessor(workers=0)
        assert processor.workers == 1
        
        processor = BatchProcessor(workers=-5)
        assert processor.workers == 1

    def test_find_video_files(self, tmp_path):
        """Test finding video files in directory."""
        # Create test files
        (tmp_path / "video1.mp4").touch()
        (tmp_path / "video2.mkv").touch()
        (tmp_path / "document.txt").touch()
        (tmp_path / "image.png").touch()
        
        processor = BatchProcessor()
        files = processor.find_video_files(str(tmp_path))
        
        assert len(files) == 2
        assert any("video1.mp4" in f for f in files)
        assert any("video2.mkv" in f for f in files)

    def test_find_video_files_custom_extensions(self, tmp_path):
        """Test finding video files with custom extensions."""
        (tmp_path / "video1.mp4").touch()
        (tmp_path / "video2.mkv").touch()
        (tmp_path / "video3.avi").touch()
        
        processor = BatchProcessor(extensions=["mp4"])
        files = processor.find_video_files(str(tmp_path))
        
        assert len(files) == 1
        assert any("video1.mp4" in f for f in files)

    def test_find_video_files_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        processor = BatchProcessor()
        files = processor.find_video_files(str(tmp_path))
        
        assert files == []


class TestBatchState:
    """Tests for BatchState dataclass."""

    def test_state_creation(self):
        """Test creating batch state."""
        state = BatchState(
            input_dir="/videos",
            output_dir="/subs",
            model="base",
            output_format="vtt",
        )
        
        assert state.input_dir == "/videos"
        assert state.output_dir == "/subs"
        assert state.model == "base"
        assert state.output_format == "vtt"
        assert state.processed_files == []
        assert state.failed_files == []

    def test_state_to_dict(self):
        """Test converting state to dictionary."""
        state = BatchState(
            input_dir="/videos",
            output_dir="/subs",
            model="base",
            output_format="vtt",
        )
        
        data = state.to_dict()
        
        assert data["input_dir"] == "/videos"
        assert data["output_dir"] == "/subs"
        assert "started_at" in data

    def test_state_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "input_dir": "/videos",
            "output_dir": "/subs",
            "model": "base",
            "output_format": "vtt",
            "started_at": "2024-01-01T00:00:00",
            "processed_files": ["/videos/a.mp4"],
            "failed_files": [],
            "results": [],
        }
        
        state = BatchState.from_dict(data)
        
        assert state.input_dir == "/videos"
        assert state.processed_files == ["/videos/a.mp4"]

    def test_state_save_and_load(self, tmp_path):
        """Test saving and loading state."""
        state_path = str(tmp_path / "state.json")
        
        state = BatchState(
            input_dir="/videos",
            output_dir="/subs",
            model="base",
            output_format="vtt",
        )
        state.processed_files.append("/videos/video1.mp4")
        state.save(state_path)
        
        loaded = BatchState.load(state_path)
        
        assert loaded is not None
        assert loaded.input_dir == "/videos"
        assert loaded.processed_files == ["/videos/video1.mp4"]

    def test_state_load_nonexistent(self, tmp_path):
        """Test loading non-existent state file."""
        state_path = str(tmp_path / "nonexistent.json")
        
        loaded = BatchState.load(state_path)
        
        assert loaded is None


class TestBatchFileResult:
    """Tests for BatchFileResult dataclass."""

    def test_success_result(self):
        """Test creating success result."""
        result = BatchFileResult(
            file_path="/videos/video.mp4",
            success=True,
            output_path="/subs/video.vtt",
            duration_seconds=10.5,
        )
        
        assert result.success is True
        assert result.output_path == "/subs/video.vtt"
        assert result.error is None

    def test_failure_result(self):
        """Test creating failure result."""
        result = BatchFileResult(
            file_path="/videos/video.mp4",
            success=False,
            error="Transcription failed",
            duration_seconds=5.0,
        )
        
        assert result.success is False
        assert result.error == "Transcription failed"


class TestBatchSummary:
    """Tests for BatchSummary dataclass."""

    def test_summary_creation(self):
        """Test creating summary."""
        results = [
            BatchFileResult("/v1.mp4", True, "/v1.vtt", duration_seconds=10),
            BatchFileResult("/v2.mp4", False, error="Failed", duration_seconds=5),
        ]
        
        summary = BatchSummary(
            total_files=3,
            successful=1,
            failed=1,
            skipped=1,
            total_duration_seconds=15.0,
            results=results,
        )
        
        assert summary.total_files == 3
        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_generate_report(self):
        """Test generating markdown report."""
        results = [
            BatchFileResult("/v1.mp4", True, "/v1.vtt", duration_seconds=10),
        ]
        
        summary = BatchSummary(
            total_files=1,
            successful=1,
            failed=0,
            skipped=0,
            total_duration_seconds=10.0,
            results=results,
        )
        
        report = summary.generate_report()
        
        assert "# Batch Processing Summary" in report
        assert "| Total Files | 1 |" in report
        assert "| Successful | 1 |" in report
        assert "✅ Success" in report
