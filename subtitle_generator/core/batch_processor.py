"""
Batch processing module for processing multiple videos simultaneously.

Provides parallel processing with configurable workers, progress tracking,
resume capability, and summary report generation.
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from threading import Lock
from typing import Callable, Optional

from ..utils.file_handler import (
    ensure_directory,
    directory_exists,
    list_files_with_extension,
    get_file_basename,
)
from ..utils.exceptions import SubtitleError

logger = logging.getLogger(__name__)


# Video extensions to process
DEFAULT_VIDEO_EXTENSIONS = ["mp4", "mkv", "avi", "mov", "webm", "m4v", "flv", "wmv"]


@dataclass
class BatchFileResult:
    """Result of processing a single file in batch."""
    
    file_path: str
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BatchState:
    """State of a batch processing job for resume capability."""
    
    input_dir: str
    output_dir: str
    model: str
    output_format: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "BatchState":
        """Create state from dictionary."""
        return cls(**data)
    
    def save(self, state_path: str) -> None:
        """Save state to file."""
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, state_path: str) -> Optional["BatchState"]:
        """Load state from file if it exists."""
        if not os.path.exists(state_path):
            return None
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load batch state: {e}")
            return None


@dataclass
class BatchSummary:
    """Summary of batch processing results."""
    
    total_files: int
    successful: int
    failed: int
    skipped: int
    total_duration_seconds: float
    results: list[BatchFileResult]
    
    def generate_report(self) -> str:
        """Generate a markdown report of the batch processing."""
        lines = [
            "# Batch Processing Summary",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Files | {self.total_files} |",
            f"| Successful | {self.successful} |",
            f"| Failed | {self.failed} |",
            f"| Skipped | {self.skipped} |",
            f"| Total Duration | {self.total_duration_seconds:.2f}s |",
            "",
        ]
        
        if self.results:
            lines.extend([
                "## Processed Files",
                "",
                "| File | Status | Duration | Output |",
                "|------|--------|----------|--------|",
            ])
            
            for result in self.results:
                status = "✅ Success" if result.success else f"❌ {result.error or 'Failed'}"
                duration = f"{result.duration_seconds:.2f}s"
                output = os.path.basename(result.output_path) if result.output_path else "-"
                file_name = os.path.basename(result.file_path)
                lines.append(f"| {file_name} | {status} | {duration} | {output} |")
        
        return "\n".join(lines)


class BatchProcessor:
    """
    Process multiple videos in parallel with progress tracking.
    
    Features:
    - Parallel processing with configurable workers
    - Progress callback for each file
    - Resume capability for interrupted batches
    - Summary report generation
    """
    
    STATE_FILE_NAME = ".batch_state.json"
    REPORT_FILE_NAME = "batch_report.md"
    
    def __init__(
        self,
        workers: int = 4,
        model: str = "base",
        output_format: str = "vtt",
        extensions: Optional[list[str]] = None,
        whisper_binary: Optional[str] = None,
        models_dir: Optional[str] = None,
        language: Optional[str] = None,
        translate: bool = False,
    ):
        """
        Initialize the batch processor.

        Args:
            workers: Number of parallel workers
            model: Whisper model to use
            output_format: Output subtitle format
            extensions: Video file extensions to process
            whisper_binary: Optional override for the whisper-cli binary path.
                Falls back to env / PATH discovery (see ``utils.paths``).
            models_dir: Optional override for the models cache directory.
            language: Spoken language code (e.g., 'en', 'es', 'auto')
            translate: Translate speech to English
        """
        self.workers = max(1, workers)
        self.model = model
        self.output_format = output_format
        self.extensions = extensions or DEFAULT_VIDEO_EXTENSIONS
        self.whisper_binary = whisper_binary
        self.models_dir = models_dir
        self.language = language
        self.translate = translate
        self._state_lock = Lock()
    
    def find_video_files(self, input_dir: str) -> list[str]:
        """
        Find all video files in the input directory.
        
        Args:
            input_dir: Directory to search for videos
            
        Returns:
            List of video file paths
        """
        video_files = []
        for ext in self.extensions:
            video_files.extend(list_files_with_extension(input_dir, ext, recursive=False))
        return sorted(video_files)
    
    def _get_state_path(self, output_dir: str) -> str:
        """Get the path to the batch state file."""
        return os.path.join(output_dir, self.STATE_FILE_NAME)
    
    def _get_report_path(self, output_dir: str) -> str:
        """Get the path to the batch report file."""
        return os.path.join(output_dir, self.REPORT_FILE_NAME)
    
    def process_batch(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        resume: bool = False,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> BatchSummary:
        """
        Process all videos in the input directory.
        
        Args:
            input_dir: Directory containing video files
            output_dir: Directory for output files (default: same as input)
            resume: Whether to resume from previous state
            progress_callback: Callback(file_path, current, total, status) for progress updates
            
        Returns:
            BatchSummary with processing results
        """
        # Validate input directory
        if not directory_exists(input_dir):
            raise SubtitleError(f"Input directory does not exist: {input_dir}")
        
        # Set output directory
        output_dir = output_dir or input_dir
        ensure_directory(output_dir)
        
        # Find video files
        video_files = self.find_video_files(input_dir)
        if not video_files:
            logger.warning(f"No video files found in {input_dir}")
            return BatchSummary(
                total_files=0,
                successful=0,
                failed=0,
                skipped=0,
                total_duration_seconds=0.0,
                results=[],
            )
        
        # Load or create state
        state_path = self._get_state_path(output_dir)
        state: Optional[BatchState] = None
        
        if resume:
            state = BatchState.load(state_path)
            if state:
                logger.info(f"Resuming batch: {len(state.processed_files)} already processed")
        
        if not state:
            state = BatchState(
                input_dir=input_dir,
                output_dir=output_dir,
                model=self.model,
                output_format=self.output_format,
            )
        
        # Filter out already processed files if resuming
        files_to_process = [
            f for f in video_files 
            if f not in state.processed_files and f not in state.failed_files
        ]
        skipped = len(video_files) - len(files_to_process)
        
        # Process files
        results: list[BatchFileResult] = []
        total = len(files_to_process)
        start_time = time.time()
        
        if self.workers == 1 or total <= 1:
            for idx, file_path in enumerate(files_to_process, 1):
                if progress_callback:
                    progress_callback(file_path, idx, total, "processing")
                
                result = self._process_single_file(file_path, output_dir)
                results.append(result)
                
                self._record_result(state, state_path, result)
                
                if progress_callback:
                    status = "complete" if result.success else f"failed: {result.error}"
                    progress_callback(file_path, idx, total, status)
        else:
            completed_count = 0
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_file = {}
                for idx, file_path in enumerate(files_to_process, 1):
                    if progress_callback:
                        progress_callback(file_path, idx, total, "processing")
                    future = executor.submit(self._process_single_file, file_path, output_dir)
                    future_to_file[future] = file_path
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    result = future.result()
                    with self._state_lock:
                        completed_count += 1
                        current = completed_count
                        results.append(result)
                        self._record_result(state, state_path, result)
                        if progress_callback:
                            status = "complete" if result.success else f"failed: {result.error}"
                            progress_callback(file_path, current, total, status)
        
        total_duration = time.time() - start_time
        
        # Create summary
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        summary = BatchSummary(
            total_files=len(video_files),
            successful=successful,
            failed=failed,
            skipped=skipped,
            total_duration_seconds=total_duration,
            results=results,
        )
        
        # Generate report
        report_path = self._get_report_path(output_dir)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(summary.generate_report())
        logger.info(f"Batch report saved to: {report_path}")
        
        # Clean up state file on successful completion
        if failed == 0 and os.path.exists(state_path):
            os.remove(state_path)
        
        return summary
    
    def _record_result(
        self,
        state: BatchState,
        state_path: str,
        result: BatchFileResult,
    ) -> None:
        """Record a single file result into state and persist to disk."""
        if result.success:
            state.processed_files.append(result.file_path)
        else:
            state.failed_files.append(result.file_path)
        state.results.append(asdict(result))
        state.save(state_path)
    
    def _process_single_file(
        self,
        file_path: str,
        output_dir: str,
    ) -> BatchFileResult:
        """
        Process a single video file.
        
        Args:
            file_path: Path to the video file
            output_dir: Directory for output
            
        Returns:
            BatchFileResult with processing outcome
        """
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from .transcriber import WhisperCppTranscriber
            from .subtitle_gen import SubtitleGenerator
            from ..models import ModelManager
            from ..utils.paths import default_output_dir
            
            transcriber = WhisperCppTranscriber(
                binary_path=self.whisper_binary,
                language=self.language,
                translate=self.translate,
            )
            model_manager = ModelManager(models_dir=self.models_dir)
            generator = SubtitleGenerator(transcriber, model_manager)
            
            base_name = get_file_basename(file_path)
            final_output = os.path.join(output_dir, f"{base_name}.{self.output_format}")
            
            output_path, success = generator.generate_and_rename(
                input_path=file_path,
                model_name=self.model,
                output_format=self.output_format,
                output_dir=default_output_dir(),
                output_path=final_output,
                language=self.language,
                translate=self.translate,
            )
            
            duration = time.time() - start_time
            
            if success:
                return BatchFileResult(
                    file_path=file_path,
                    success=True,
                    output_path=output_path,
                    duration_seconds=duration,
                )
            else:
                return BatchFileResult(
                    file_path=file_path,
                    success=False,
                    error="Transcription failed",
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
