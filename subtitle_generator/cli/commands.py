"""
CLI module with Observer pattern for progress tracking.

Provides a clean command-line interface for the subtitle generator
with progress callbacks and rich output.
"""

import argparse
import logging
import sys
from abc import ABC, abstractmethod
from typing import Optional

from ..core.transcriber import WhisperCppTranscriber
from ..core.subtitle_gen import SubtitleGenerator
from ..core.video_processor import VideoProcessor
from ..core.batch_processor import BatchProcessor
from ..models import ModelManager
from ..utils.downloader import is_url, download_file
from ..utils.exceptions import TranscriptionError
from ..utils.file_handler import sanitize_filename, file_exists, directory_exists
from ..utils.paths import default_output_dir
from ..utils.validators import (
    validate_media_path,
    validate_model_name,
    validate_output_format,
    get_available_models,
    get_supported_formats,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Observer Pattern for Progress Tracking
# ============================================================================

class ProgressObserver(ABC):
    """Abstract observer for progress updates."""
    
    @abstractmethod
    def on_progress(self, stage: str, progress: float, message: str = ""):
        """Called when progress is updated."""
        pass
    
    @abstractmethod
    def on_complete(self, success: bool, result: Optional[str] = None):
        """Called when processing completes."""
        pass
    
    @abstractmethod
    def on_error(self, error: str):
        """Called when an error occurs."""
        pass


class ConsoleProgressObserver(ProgressObserver):
    """Console-based progress observer with pretty output."""
    
    STAGE_LABELS = {
        "preparing": "[PREP]",
        "downloading": "[DOWN]",
        "transcribing": "[TRANS]",
        "merging": "[MERGE]",
        "complete": "[DONE]",
        "error": "[ERROR]",
    }
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def on_progress(self, stage: str, progress: float, message: str = ""):
        label = self.STAGE_LABELS.get(stage, "[...]")
        percentage = f"{progress * 100:.0f}%" if progress > 0 else ""
        
        status = f"{label} {stage.capitalize()}"
        if percentage:
            status += f" {percentage}"
        if message and self.verbose:
            status += f" - {message}"
        
        print(f"\r{status}", end="", flush=True)
        if progress >= 1.0:
            print()
    
    def on_complete(self, success: bool, result: Optional[str] = None):
        if success:
            label = self.STAGE_LABELS["complete"]
            print(f"\n{label} Success!")
            if result:
                print(f"   Output: {result}")
        else:
            label = self.STAGE_LABELS["error"]
            print(f"\n{label} Failed")
    
    def on_error(self, error: str):
        label = self.STAGE_LABELS["error"]
        print(f"\n{label} Error: {error}", file=sys.stderr)


class SilentProgressObserver(ProgressObserver):
    """Silent observer that captures results without output."""
    
    def __init__(self):
        self.stages = []
        self.errors = []
        self.result = None
        self.success = False
    
    def on_progress(self, stage: str, progress: float, message: str = ""):
        self.stages.append((stage, progress, message))
    
    def on_complete(self, success: bool, result: Optional[str] = None):
        self.success = success
        self.result = result
    
    def on_error(self, error: str):
        self.errors.append(error)


# ============================================================================
# CLI Class
# ============================================================================

class SubtitleCLI:
    """Command-line interface for subtitle generation."""
    
    def __init__(
        self,
        observer: Optional[ProgressObserver] = None,
        models_dir: Optional[str] = None,
        whisper_binary: Optional[str] = None,
    ):
        self.observer = observer or ConsoleProgressObserver()
        # `whisper_binary` is plumbed through to `WhisperCppTranscriber` so
        # users can override the binary location via --whisper-binary or
        # SUBTITLE_WHISPER_BINARY. `models_dir` is plumbed through to
        # `ModelManager` so models can be cached anywhere the user prefers.
        self.whisper_binary = whisper_binary
        self.model_manager = ModelManager(models_dir=models_dir)
    
    def run(self, args: argparse.Namespace) -> int:
        """Run the CLI with parsed arguments."""
        try:
            # Handle subcommands
            if hasattr(args, "command") and args.command:
                if args.command == "models":
                    return self._handle_models_command(args)
                elif args.command == "formats":
                    return self._handle_formats_command()
                elif args.command == "batch":
                    return self._handle_batch_command(args)
            
            # Default: process video
            return self._handle_process_command(args)
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            return 130
        except Exception as e:
            self.observer.on_error(str(e))
            logger.exception("Unexpected error")
            return 1
    
    def _handle_process_command(self, args: argparse.Namespace) -> int:
        """Handle the main process command."""
        filepath = args.filepath
        model = args.model
        output_format = args.format
        merge = args.merge
        
        if not filepath:
            self.observer.on_error("No video file specified")
            return 1
        
        # Handle URL input
        if is_url(filepath):
            self.observer.on_progress("downloading", 0.0)
            try:
                filepath = download_file(filepath, show_progress=True)
                self.observer.on_progress("downloading", 1.0)
            except Exception as e:
                self.observer.on_error(f"Download failed: {e}")
                return 1
        
        # Sanitize filename if needed
        if " " in filepath:
            new_path = sanitize_filename(filepath)
            if new_path != filepath:
                import os
                os.rename(filepath, new_path)
                filepath = new_path
        
        # Validate inputs
        valid, error = validate_media_path(filepath)
        if not valid:
            self.observer.on_error(error)
            return 1
        
        valid, error = validate_model_name(model)
        if not valid:
            self.observer.on_error(error)
            return 1
        
        valid, error = validate_output_format(output_format)
        if not valid:
            self.observer.on_error(error)
            return 1
        
        # Create transcriber and generator. Binary discovery happens here
        # (not in ModelManager / SubtitleGenerator) so that a misconfiguration
        # surfaces with a clear, actionable message before we waste time
        # downloading models.
        try:
            transcriber = WhisperCppTranscriber(
                binary_path=self.whisper_binary,
                threads=args.threads,
                processors=args.processors,
            )
        except TranscriptionError as e:
            self.observer.on_error(str(e))
            return 1
        generator = SubtitleGenerator(transcriber, self.model_manager)

        def progress_callback(stage: str, progress: float):
            self.observer.on_progress(stage, progress)

        subtitle_path, success = generator.generate_and_rename(
            input_path=filepath,
            model_name=model,
            output_format=output_format,
            output_dir=default_output_dir(),
            progress_callback=progress_callback,
        )
        
        if not success:
            self.observer.on_error("Transcription failed")
            return 1
        
        # Merge subtitles into video if requested
        if merge:
            self.observer.on_progress("merging", 0.0)
            processor = VideoProcessor()
            
            import os
            base, ext = os.path.splitext(filepath)
            output_path = f"{base}_subtitled{ext}"
            
            if processor.merge_subtitles(filepath, subtitle_path, output_path):
                self.observer.on_progress("merging", 1.0)
                self.observer.on_complete(True, output_path)
            else:
                self.observer.on_error("Failed to merge subtitles")
                return 1
        else:
            self.observer.on_complete(True, subtitle_path)
        
        return 0
    
    def _handle_models_command(self, args: argparse.Namespace) -> int:
        """Handle the models subcommand."""
        if hasattr(args, 'list') and args.list:
            available = self.model_manager.list_available_models()
            downloaded = self.model_manager.list_downloaded_models()
            
            print("Available models:")
            for model in available:
                status = "x" if model in downloaded else " "
                print(f"  [{status}] {model}")
            
            print(f"\nDownloaded: {len(downloaded)}/{len(available)}")
            return 0
        
        if hasattr(args, 'download') and args.download:
            model_name = args.download
            valid, error = validate_model_name(model_name)
            if not valid:
                self.observer.on_error(error)
                return 1
            
            try:
                path = self.model_manager.download_model(model_name)
                print(f"Downloaded: {path}")
                return 0
            except Exception as e:
                self.observer.on_error(str(e))
                return 1
        
        # Default: list models
        return self._handle_models_command(argparse.Namespace(list=True, download=None))
    
    def _handle_formats_command(self) -> int:
        """Handle the formats subcommand."""
        formats = get_supported_formats()
        print("Supported subtitle formats:")
        for fmt in formats:
            print(f"  - {fmt}")
        return 0
    
    def _handle_batch_command(self, args: argparse.Namespace) -> int:
        """Handle the batch subcommand."""
        input_dir = args.input_dir
        output_dir = args.output_dir or input_dir
        workers = args.workers
        model = args.model
        output_format = args.format
        resume = args.resume
        extensions = args.extensions.split(",") if args.extensions else None
        
        # Validate input directory
        if not directory_exists(input_dir):
            self.observer.on_error(f"Input directory does not exist: {input_dir}")
            return 1
        
        # Validate model
        valid, error = validate_model_name(model)
        if not valid:
            self.observer.on_error(error)
            return 1
        
        # Validate output format
        valid, error = validate_output_format(output_format)
        if not valid:
            self.observer.on_error(error)
            return 1
        
        processor = BatchProcessor(
            workers=workers,
            model=model,
            output_format=output_format,
            extensions=extensions,
            whisper_binary=self.whisper_binary,
            models_dir=self.model_manager.models_dir,
        )
        
        # Find files first to show count
        video_files = processor.find_video_files(input_dir)
        if not video_files:
            print(f"No video files found in {input_dir}")
            return 0
        
        print(f"Found {len(video_files)} video files")
        print(f"Output directory: {output_dir}")
        print(f"Model: {model}, Format: {output_format}, Workers: {workers}")
        if resume:
            print("Resume mode: enabled")
        print()
        
        # Progress callback
        def progress_callback(file_path: str, current: int, total: int, status: str):
            filename = file_path.split("/")[-1]
            print(f"[{current}/{total}] {filename}: {status}")
        
        # Process batch
        try:
            summary = processor.process_batch(
                input_dir=input_dir,
                output_dir=output_dir,
                resume=resume,
                progress_callback=progress_callback,
            )
            
            # Print summary
            print()
            print("=" * 50)
            print("BATCH PROCESSING COMPLETE")
            print("=" * 50)
            print(f"Total files:  {summary.total_files}")
            print(f"Successful:   {summary.successful}")
            print(f"Failed:       {summary.failed}")
            print(f"Skipped:      {summary.skipped}")
            print(f"Duration:     {summary.total_duration_seconds:.2f}s")
            print()
            print(f"Report saved to: {output_dir}/batch_report.md")
            
            return 0 if summary.failed == 0 else 1
            
        except Exception as e:
            self.observer.on_error(str(e))
            return 1


# ============================================================================
# Main Entry Point
# ============================================================================

def create_main_parser() -> argparse.ArgumentParser:
    """Create parser for main video processing commands."""
    parser = argparse.ArgumentParser(
        prog="subtitle",
        description="Generate subtitles for video files using Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
First-time setup (one-time):
  subtitle setup-whisper                Build the whisper-cli binary

Examples:
  subtitle video.mp4                    Generate VTT subtitles
  subtitle video.mp4 --merge            Generate and embed subtitles
  subtitle video.mp4 --model small      Use small model
  subtitle video.mp4 --format srt       Generate SRT format
  subtitle models --list                List available models
  subtitle models --download large      Download large model
  subtitle formats                      List supported formats
        """,
    )
    
    parser.add_argument(
        "filepath",
        type=str,
        nargs="?",
        default=None,
        help="Path to video file or URL",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="base",
        help="Whisper model to use (default: base)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="vtt",
        help="Output subtitle format (default: vtt)",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge subtitles into video file",
    )
    parser.add_argument(
        "--threads", "-t",
        type=int,
        default=4,
        help="Number of threads (default: 4)",
    )
    parser.add_argument(
        "--processors", "-p",
        type=int,
        default=1,
        help="Number of processors (default: 1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--whisper-binary",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to the whisper-cli binary. Overrides the "
            "SUBTITLE_WHISPER_BINARY env var and PATH lookup."
        ),
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        metavar="DIR",
        help=(
            "Directory used to cache downloaded Whisper models. "
            "Defaults to a per-OS user cache (e.g. "
            "~/Library/Caches/subtitle-generator on macOS)."
        ),
    )

    return parser


def create_models_parser() -> argparse.ArgumentParser:
    """Create parser for models subcommand."""
    parser = argparse.ArgumentParser(
        prog="subtitle models",
        description="Manage Whisper models",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available models",
    )
    parser.add_argument(
        "--download", "-d",
        type=str,
        metavar="MODEL",
        help="Download a model",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory used to cache downloaded Whisper models",
    )
    return parser


def create_setup_whisper_parser() -> argparse.ArgumentParser:
    """Create parser for the `setup-whisper` subcommand.

    The subcommand builds whisper.cpp from source into the user data
    directory so the rest of the CLI can auto-discover the binary on
    every subsequent invocation, without manual env vars or PATH
    manipulation.
    """
    parser = argparse.ArgumentParser(
        prog="subtitle setup-whisper",
        description=(
            "Clone, build, and install the whisper.cpp CLI into your "
            "per-OS user data dir. One-time setup; auto-discovered "
            "afterwards."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  subtitle setup-whisper                       Build the default fork (recommended)
  subtitle setup-whisper --force               Wipe existing checkout and rebuild
  subtitle setup-whisper --no-pull             Rebuild offline from current sources
  subtitle setup-whisper --ref v1.7.4          Pin to a specific tag/branch/commit

Requires git, cmake, and a C++ compiler on PATH.
        """,
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        metavar="URL",
        help=(
            "Git URL of the whisper.cpp source. Defaults to the project's "
            "compatible fork (innovatorved/whisper.cpp)."
        ),
    )
    parser.add_argument(
        "--ref",
        type=str,
        default=None,
        metavar="REF",
        help="Branch, tag, or commit to check out (default: develop).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Wipe any existing checkout and re-clone from scratch.",
    )
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip `git fetch / pull` on an existing checkout (offline rebuild).",
    )
    return parser


def create_batch_parser() -> argparse.ArgumentParser:
    """Create parser for batch subcommand."""
    parser = argparse.ArgumentParser(
        prog="subtitle batch",
        description="Batch process multiple video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  subtitle batch --input-dir /videos --output-dir /subs
  subtitle batch --input-dir /videos --workers 4
  subtitle batch --input-dir /videos --resume
        """,
    )
    parser.add_argument(
        "--input-dir", "-i",
        type=str,
        required=True,
        help="Directory containing video files",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Directory for subtitle output (default: same as input)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="base",
        help="Whisper model to use (default: base)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="vtt",
        help="Output subtitle format (default: vtt)",
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume interrupted batch processing",
    )
    parser.add_argument(
        "--extensions", "-e",
        type=str,
        default=None,
        help="Comma-separated video extensions (default: mp4,mkv,avi,mov,webm)",
    )
    parser.add_argument(
        "--whisper-binary",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to the whisper-cli binary (overrides env / PATH lookup)",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory used to cache downloaded Whisper models",
    )
    return parser


def _handle_setup_whisper_command(args: argparse.Namespace) -> int:
    """Handle the ``subtitle setup-whisper`` subcommand.

    Kept at module scope (rather than as a method on ``SubtitleCLI``) so
    that triggering the build doesn't require constructing a
    ``ModelManager`` — useful when the user is running ``setup-whisper``
    precisely because nothing works yet.
    """
    # Local import: keeps the heavy build logic out of CLI startup time
    # for the 99% of invocations that aren't `setup-whisper`.
    from ..utils.whisper_setup import (
        DEFAULT_REF,
        DEFAULT_REPO_URL,
        WhisperSetupError,
        setup_whisper,
    )

    repo = args.repo or DEFAULT_REPO_URL
    ref = args.ref or DEFAULT_REF
    force = bool(args.force)
    pull = not bool(getattr(args, "no_pull", False))

    print(f"[setup-whisper] repo={repo} ref={ref} force={force} pull={pull}")

    def _stream(line: str) -> None:
        print(line, flush=True)

    try:
        result = setup_whisper(
            repo_url=repo,
            ref=ref,
            force=force,
            pull=pull,
            log_callback=_stream,
        )
    except WhisperSetupError as e:
        print(f"\n[ERROR] setup-whisper failed: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.", file=sys.stderr)
        return 130

    print(
        "\n[DONE] whisper-cli installed.\n"
        f"  binary: {result.binary_path}\n"
        f"  source: {result.source_dir}\n"
        f"  ref:    {result.ref}\n"
        "You can now run `subtitle <video>` from anywhere — the binary "
        "will be auto-discovered."
    )
    return 0


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for CLI."""
    if args is None:
        args = sys.argv[1:]
    
    # Check for subcommands first
    if args and args[0] == "models":
        parser = create_models_parser()
        parsed_args = parser.parse_args(args[1:])
        parsed_args.command = "models"
        observer = ConsoleProgressObserver()
        cli = SubtitleCLI(observer, models_dir=parsed_args.models_dir)
        return cli.run(parsed_args)

    if args and args[0] == "formats":
        cli = SubtitleCLI()
        return cli._handle_formats_command()

    if args and args[0] == "setup-whisper":
        parser = create_setup_whisper_parser()
        parsed_args = parser.parse_args(args[1:])
        return _handle_setup_whisper_command(parsed_args)

    if args and args[0] == "batch":
        parser = create_batch_parser()
        parsed_args = parser.parse_args(args[1:])
        parsed_args.command = "batch"
        observer = ConsoleProgressObserver()
        cli = SubtitleCLI(
            observer,
            models_dir=parsed_args.models_dir,
            whisper_binary=parsed_args.whisper_binary,
        )
        return cli.run(parsed_args)

    # Main parser for video processing
    parser = create_main_parser()
    parsed_args = parser.parse_args(args)
    parsed_args.command = None

    # Show help if no arguments
    if parsed_args.filepath is None:
        parser.print_help()
        return 0

    observer = ConsoleProgressObserver(verbose=parsed_args.verbose)

    cli = SubtitleCLI(
        observer,
        models_dir=parsed_args.models_dir,
        whisper_binary=parsed_args.whisper_binary,
    )
    return cli.run(parsed_args)


if __name__ == "__main__":
    sys.exit(main())
