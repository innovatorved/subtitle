"""
Async processor module for concurrent video processing.

Provides asynchronous video processing using asyncio and ProcessPoolExecutor
for true parallel subtitle generation across multiple videos.
"""

import asyncio
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, List, Optional

from .batch_processor import BatchFileResult, BatchSummary
from ..utils.exceptions import SubtitleError

logger = logging.getLogger(__name__)


def _process_single_video(
    file_path: str,
    output_dir: str,
    model: str,
    output_format: str,
) -> BatchFileResult:
    """
    Process a single video file in a separate process.
    
    This function is designed to be called via ProcessPoolExecutor.
    Must be at module level for pickling.
    
    Args:
        file_path: Path to the video file
        output_dir: Directory for output
        model: Whisper model to use
        output_format: Output subtitle format
        
    Returns:
        BatchFileResult with processing outcome
    """
    start_time = time.time()
    
    try:
        # Import here to avoid issues with process spawning
        from .transcriber import WhisperCppTranscriber
        from .subtitle_gen import SubtitleGenerator
        from ..models import ModelManager
        from ..utils.file_handler import get_file_basename
        import os
        
        # Create generator
        transcriber = WhisperCppTranscriber()
        model_manager = ModelManager()
        generator = SubtitleGenerator(transcriber, model_manager)
        
        # Generate subtitles
        result = generator.generate(
            input_path=file_path,
            model_name=model,
            output_format=output_format,
            output_dir=output_dir,
        )
        
        duration = time.time() - start_time
        
        if result.success:
            # Rename output to match input filename
            base_name = get_file_basename(file_path)
            final_output = os.path.join(output_dir, f"{base_name}.{output_format}")
            
            if result.output_path and os.path.exists(result.output_path):
                if result.output_path != final_output:
                    os.rename(result.output_path, final_output)
                return BatchFileResult(
                    file_path=file_path,
                    success=True,
                    output_path=final_output,
                    duration_seconds=duration,
                )
            return BatchFileResult(
                file_path=file_path,
                success=True,
                output_path=result.output_path,
                duration_seconds=duration,
            )
        else:
            return BatchFileResult(
                file_path=file_path,
                success=False,
                error=result.error or "Transcription failed",
                duration_seconds=duration,
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error processing {file_path}: {e}")
        return BatchFileResult(
            file_path=file_path,
            success=False,
            error=str(e),
            duration_seconds=duration,
        )


class AsyncProcessor:
    """
    Asynchronous video processing with concurrent execution.
    
    Uses ProcessPoolExecutor for true parallelism since video transcription
    is CPU-bound. Integrates with asyncio for non-blocking concurrent operations.
    
    Example:
        async def main():
            processor = AsyncProcessor(max_workers=4)
            try:
                results = await processor.process_multiple(
                    video_paths=["video1.mp4", "video2.mp4"],
                    model="base",
                )
                for result in results:
                    print(f"{result.file_path}: {'✓' if result.success else '✗'}")
            finally:
                processor.shutdown()
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the async processor.
        
        Args:
            max_workers: Maximum number of parallel workers (default: 4)
        """
        self.max_workers = max(1, max_workers)
        self._executor: Optional[ProcessPoolExecutor] = None
    
    @property
    def executor(self) -> ProcessPoolExecutor:
        """Lazily create the executor to defer process spawning."""
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self._executor
    
    async def process_single(
        self,
        video_path: str,
        model: str = "base",
        output_format: str = "vtt",
        output_dir: Optional[str] = None,
    ) -> BatchFileResult:
        """
        Process a single video asynchronously.
        
        Args:
            video_path: Path to the video file
            model: Whisper model to use
            output_format: Output subtitle format
            output_dir: Directory for output (default: same as input)
            
        Returns:
            BatchFileResult with processing outcome
        """
        if not Path(video_path).exists():
            return BatchFileResult(
                file_path=video_path,
                success=False,
                error=f"File not found: {video_path}",
            )
        
        output_dir = output_dir or str(Path(video_path).parent)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            _process_single_video,
            video_path,
            output_dir,
            model,
            output_format,
        )
        
        return result
    
    async def process_multiple(
        self,
        video_paths: List[str],
        model: str = "base",
        output_format: str = "vtt",
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> BatchSummary:
        """
        Process multiple videos concurrently.
        
        Args:
            video_paths: List of paths to video files
            model: Whisper model to use
            output_format: Output subtitle format
            output_dir: Directory for output (default: same as input for each file)
            progress_callback: Callback(file_path, current, total, status) for progress
            
        Returns:
            BatchSummary with all processing results
        """
        if not video_paths:
            return BatchSummary(
                total_files=0,
                successful=0,
                failed=0,
                skipped=0,
                total_duration_seconds=0.0,
                results=[],
            )
        
        start_time = time.time()
        total = len(video_paths)
        results: List[BatchFileResult] = []
        
        # Create tasks for all videos
        loop = asyncio.get_event_loop()
        tasks = []
        
        for video_path in video_paths:
            file_output_dir = output_dir or str(Path(video_path).parent)
            task = loop.run_in_executor(
                self.executor,
                _process_single_video,
                video_path,
                file_output_dir,
                model,
                output_format,
            )
            tasks.append((video_path, task))
        
        # Process with progress tracking
        for idx, (video_path, task) in enumerate(tasks, 1):
            if progress_callback:
                progress_callback(video_path, idx, total, "processing")
            
            try:
                result = await task
                results.append(result)
                
                if progress_callback:
                    status = "complete" if result.success else f"failed: {result.error}"
                    progress_callback(video_path, idx, total, status)
                    
            except Exception as e:
                logger.error(f"Task failed for {video_path}: {e}")
                results.append(BatchFileResult(
                    file_path=video_path,
                    success=False,
                    error=str(e),
                ))
                if progress_callback:
                    progress_callback(video_path, idx, total, f"failed: {e}")
        
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        return BatchSummary(
            total_files=total,
            successful=successful,
            failed=failed,
            skipped=0,
            total_duration_seconds=total_duration,
            results=results,
        )
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the executor and release resources.
        
        Args:
            wait: If True, wait for pending tasks to complete
        """
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None
    
    async def __aenter__(self) -> "AsyncProcessor":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        self.shutdown(wait=True)
