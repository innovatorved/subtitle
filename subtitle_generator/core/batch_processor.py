"""Batch processing module for processing multiple media files in parallel.

Features:
- Smart CPU/GPU worker & thread budgeting to avoid thrashing or OOM
- Recursive directory discovery across video & audio formats
- Optional soft-merge (`--merge`) or hard-burn (`--burn`) in batch mode
- Resume capability with thread-safe state persistence and markdown report
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock
from typing import Callable, Optional

from ..utils.exceptions import SubtitleError
from ..utils.file_handler import (
    directory_exists,
    ensure_directory,
    get_file_basename,
    list_files_with_extension,
)
from ..utils.validators import MEDIA_EXTENSIONS

logger = logging.getLogger(__name__)

# Video + audio extensions processed by default
DEFAULT_VIDEO_EXTENSIONS = sorted(MEDIA_EXTENSIONS)


def compute_optimal_thread_budget(workers: int, explicit_threads: Optional[int] = None) -> int:
    """Divide available CPU cores cleanly across parallel workers."""
    if explicit_threads is not None and explicit_threads > 0:
        return explicit_threads
    cpus = os.cpu_count() or 4
    return max(1, cpus // max(1, workers))


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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BatchState":
        return cls(**data)

    def save(self, state_path: str) -> None:
        tmp_path = f"{state_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp_path, state_path)

    @classmethod
    def load(cls, state_path: str) -> Optional["BatchState"]:
        if not os.path.exists(state_path):
            return None
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:
            logger.warning("Failed to load batch state: %s", e)
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
        lines = [
            "# Batch Processing Summary",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
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
    """Process multiple video/audio files in parallel with progress tracking."""

    STATE_FILE_NAME = ".batch_state.json"
    REPORT_FILE_NAME = "batch_report.md"

    def __init__(
        self,
        workers: int = 2,
        model: str = "base",
        output_format: str = "vtt",
        extensions: Optional[list[str]] = None,
        whisper_binary: Optional[str] = None,
        models_dir: Optional[str] = None,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        threads: Optional[int] = None,
        processors: int = 1,
        recursive: bool = False,
        vad: bool = True,
        preset: Optional[str] = None,
        merge: bool = False,
        burn: bool = False,
        style: str = "clean",
        backend: str = "whisper.cpp",
    ):
        self.workers = max(1, workers)
        self.model = model
        self.output_format = output_format
        if extensions is not None:
            cleaned = [ext.strip().lstrip(".").lower() for ext in extensions if ext.strip()]
            self.extensions = cleaned or DEFAULT_VIDEO_EXTENSIONS
        else:
            self.extensions = DEFAULT_VIDEO_EXTENSIONS
        self.whisper_binary = whisper_binary
        self.models_dir = models_dir
        self.language = language
        self.translate = translate
        self.max_len = max_len
        self.split_on_word = split_on_word
        self.prompt = prompt
        self.threads = compute_optimal_thread_budget(self.workers, threads)
        self.processors = max(1, processors)
        self.recursive = recursive
        self.vad = vad
        self.preset = preset
        self.merge = merge
        self.burn = burn
        self.style = style
        self.backend = backend
        self._state_lock = Lock()

    def find_video_files(self, input_dir: str) -> list[str]:
        """Find all matching media files in the input directory."""
        media_files: list[str] = []
        for ext in self.extensions:
            media_files.extend(
                list_files_with_extension(input_dir, ext, recursive=self.recursive)
            )
        return sorted(set(media_files))

    def _get_state_path(self, output_dir: str) -> str:
        return os.path.join(output_dir, self.STATE_FILE_NAME)

    def _get_report_path(self, output_dir: str) -> str:
        return os.path.join(output_dir, self.REPORT_FILE_NAME)

    def process_batch(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        resume: bool = False,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> BatchSummary:
        if not directory_exists(input_dir):
            raise SubtitleError(f"Input directory does not exist: {input_dir}")

        self._active_input_dir = os.path.abspath(input_dir)
        output_dir = output_dir or input_dir
        ensure_directory(output_dir)

        video_files = self.find_video_files(input_dir)
        if not video_files:
            logger.warning("No media files found in %s", input_dir)
            return BatchSummary(
                total_files=0,
                successful=0,
                failed=0,
                skipped=0,
                total_duration_seconds=0.0,
                results=[],
            )

        state_path = self._get_state_path(output_dir)
        state: Optional[BatchState] = None
        if resume:
            state = BatchState.load(state_path)
            if state:
                logger.info("Resuming batch: %d already processed", len(state.processed_files))

        if not state:
            state = BatchState(
                input_dir=input_dir,
                output_dir=output_dir,
                model=self.model,
                output_format=self.output_format,
            )

        files_to_process = [
            f for f in video_files
            if f not in state.processed_files and f not in state.failed_files
        ]
        skipped = len(video_files) - len(files_to_process)

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
                        results.append(result)
                        self._record_result(state, state_path, result)
                        if progress_callback:
                            status = "complete" if result.success else f"failed: {result.error}"
                            progress_callback(file_path, completed_count, total, status)

        total_duration = time.time() - start_time
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

        report_path = self._get_report_path(output_dir)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(summary.generate_report())
        logger.info("Batch report saved to: %s", report_path)

        if failed == 0 and os.path.exists(state_path):
            os.remove(state_path)

        return summary

    def _record_result(
        self,
        state: BatchState,
        state_path: str,
        result: BatchFileResult,
    ) -> None:
        if result.success:
            state.processed_files.append(result.file_path)
        else:
            state.failed_files.append(result.file_path)
        state.results.append(asdict(result))
        state.save(state_path)

    def _process_single_file(self, file_path: str, output_dir: str) -> BatchFileResult:
        start_time = time.time()
        try:
            from ..models import ModelManager
            from ..utils.paths import default_output_dir
            from .backends import create_transcriber
            from .subtitle_gen import SubtitleGenerator
            from .video_processor import VideoProcessor

            transcriber = create_transcriber(
                backend=self.backend,
                binary_path=self.whisper_binary,
                threads=self.threads,
                processors=self.processors,
                language=self.language,
                translate=self.translate,
                max_len=self.max_len,
                split_on_word=self.split_on_word,
                prompt=self.prompt,
                vad=self.vad,
            )
            model_manager = ModelManager(models_dir=self.models_dir)
            generator = SubtitleGenerator(transcriber, model_manager)

            base_name = get_file_basename(file_path)
            target_dir = output_dir
            if self.recursive:
                parent_rel = os.path.relpath(os.path.dirname(os.path.abspath(file_path)), os.path.abspath(getattr(self, "_active_input_dir", os.path.dirname(file_path))))
                if parent_rel and parent_rel != "." and not parent_rel.startswith(".."):
                    target_dir = os.path.join(output_dir, parent_rel)
                    ensure_directory(target_dir)
            final_output = os.path.join(target_dir, f"{base_name}.{self.output_format}")

            output_path, success = generator.generate_and_rename(
                input_path=file_path,
                model_name=self.model,
                output_format=self.output_format,
                output_dir=default_output_dir(),
                output_path=final_output,
                language=self.language,
                translate=self.translate,
                max_len=self.max_len,
                split_on_word=self.split_on_word,
                prompt=self.prompt,
                vad=self.vad,
                preset=self.preset,
                style=self.style,
            )

            if success and (self.merge or self.burn):
                vp = VideoProcessor()
                in_ext = os.path.splitext(file_path)[1] or ".mp4"
                if self.burn:
                    burned = os.path.join(target_dir, f"{base_name}_burned{in_ext}")
                    if vp.burn_subtitles(file_path, output_path, burned, style=self.style):
                        output_path = burned
                    else:
                        return BatchFileResult(
                            file_path=file_path,
                            success=False,
                            error="Failed to burn subtitles",
                            duration_seconds=time.time() - start_time,
                        )
                elif self.merge:
                    merged = os.path.join(target_dir, f"{base_name}_subtitled{in_ext}")
                    if vp.merge_subtitles(file_path, output_path, merged):
                        output_path = merged
                    else:
                        return BatchFileResult(
                            file_path=file_path,
                            success=False,
                            error="Failed to merge subtitles",
                            duration_seconds=time.time() - start_time,
                        )

            duration = time.time() - start_time
            if success:
                return BatchFileResult(
                    file_path=file_path,
                    success=True,
                    output_path=output_path,
                    duration_seconds=duration,
                )
            return BatchFileResult(
                file_path=file_path,
                success=False,
                error="Transcription failed",
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Error processing %s: %s", file_path, e)
            return BatchFileResult(
                file_path=file_path,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )
