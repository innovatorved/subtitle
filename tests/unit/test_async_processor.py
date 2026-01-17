"""
Unit tests for async processor.
"""

import asyncio
import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.async_processor import AsyncProcessor
from src.core.batch_processor import BatchFileResult, BatchSummary


class TestAsyncProcessor:
    """Tests for AsyncProcessor class."""

    def test_init_default_values(self):
        """Test default initialization values."""
        processor = AsyncProcessor()
        
        assert processor.max_workers == 4
        assert processor._executor is None  # Lazy initialization
        
        processor.shutdown()

    def test_init_custom_workers(self):
        """Test custom worker count."""
        processor = AsyncProcessor(max_workers=8)
        assert processor.max_workers == 8
        processor.shutdown()

    def test_workers_minimum(self):
        """Test that workers is at least 1."""
        processor = AsyncProcessor(max_workers=0)
        assert processor.max_workers == 1
        
        processor = AsyncProcessor(max_workers=-5)
        assert processor.max_workers == 1
        
        processor.shutdown()

    def test_lazy_executor_creation(self):
        """Test that executor is created lazily."""
        processor = AsyncProcessor()
        
        # Executor should not be created yet
        assert processor._executor is None
        
        # Access executor property to trigger creation
        executor = processor.executor
        assert executor is not None
        assert processor._executor is not None
        
        processor.shutdown()

    def test_process_multiple_empty_list(self):
        """Test processing empty list returns empty summary."""
        async def run_test():
            processor = AsyncProcessor()
            try:
                summary = await processor.process_multiple([])
                
                assert isinstance(summary, BatchSummary)
                assert summary.total_files == 0
                assert summary.successful == 0
                assert summary.failed == 0
                assert summary.results == []
            finally:
                processor.shutdown()
        
        asyncio.run(run_test())

    def test_process_single_nonexistent_file(self):
        """Test processing non-existent file returns failure."""
        async def run_test():
            processor = AsyncProcessor()
            try:
                result = await processor.process_single("/nonexistent/video.mp4")
                
                assert isinstance(result, BatchFileResult)
                assert result.success is False
                assert "not found" in result.error.lower()
            finally:
                processor.shutdown()
        
        asyncio.run(run_test())

    def test_context_manager(self):
        """Test async context manager properly cleans up."""
        async def run_test():
            async with AsyncProcessor(max_workers=2) as processor:
                assert processor.max_workers == 2
            
            # Executor should be shut down after context exit
            assert processor._executor is None
        
        asyncio.run(run_test())

    def test_shutdown_idempotent(self):
        """Test that shutdown can be called multiple times safely."""
        processor = AsyncProcessor()
        
        # Access executor to create it
        _ = processor.executor
        
        # Multiple shutdown calls should not raise
        processor.shutdown()
        processor.shutdown()
        processor.shutdown()
        
        assert processor._executor is None

    def test_progress_callback(self):
        """Test progress callback is called with correct arguments."""
        async def run_test():
            processor = AsyncProcessor()
            callback_calls = []
            
            def progress_callback(file_path, current, total, status):
                callback_calls.append({
                    "file_path": file_path,
                    "current": current,
                    "total": total,
                    "status": status,
                })
            
            try:
                # Process non-existent files to trigger callbacks without actual processing
                await processor.process_multiple(
                    ["/fake/video1.mp4", "/fake/video2.mp4"],
                    progress_callback=progress_callback,
                )
                
                # Should have "processing" and "complete/failed" calls for each file
                assert len(callback_calls) >= 2
                assert any("processing" in c["status"] for c in callback_calls)
            finally:
                processor.shutdown()
        
        asyncio.run(run_test())


class TestBatchFileResultIntegration:
    """Test BatchFileResult usage in async context."""

    def test_result_creation_success(self):
        """Test creating success result."""
        result = BatchFileResult(
            file_path="/videos/video.mp4",
            success=True,
            output_path="/subs/video.vtt",
            duration_seconds=10.5,
        )
        
        assert result.success is True
        assert result.output_path == "/subs/video.vtt"

    def test_result_creation_failure(self):
        """Test creating failure result."""
        result = BatchFileResult(
            file_path="/videos/video.mp4",
            success=False,
            error="Processing failed",
            duration_seconds=5.0,
        )
        
        assert result.success is False
        assert result.error == "Processing failed"

