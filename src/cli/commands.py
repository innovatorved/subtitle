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
from ..models import ModelManager
from ..utils.downloader import is_url, download_file
from ..utils.file_handler import sanitize_filename, file_exists
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
    
    def __init__(self, observer: Optional[ProgressObserver] = None):
        self.observer = observer or ConsoleProgressObserver()
        self.model_manager = ModelManager()
    
    def run(self, args: argparse.Namespace) -> int:
        """Run the CLI with parsed arguments."""
        try:
            # Handle subcommands
            if hasattr(args, "command") and args.command:
                if args.command == "models":
                    return self._handle_models_command(args)
                elif args.command == "formats":
                    return self._handle_formats_command()
            
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
        
        # Create transcriber and generator
        transcriber = WhisperCppTranscriber(
            threads=args.threads,
            processors=args.processors,
        )
        generator = SubtitleGenerator(transcriber, self.model_manager)
        
        # Generate subtitles
        def progress_callback(stage: str, progress: float):
            self.observer.on_progress(stage, progress)
        
        subtitle_path, success = generator.generate_and_rename(
            input_path=filepath,
            model_name=model,
            output_format=output_format,
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
    return parser


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
        cli = SubtitleCLI(observer)
        return cli.run(parsed_args)
    
    if args and args[0] == "formats":
        cli = SubtitleCLI()
        return cli._handle_formats_command()
    
    # Main parser for video processing
    parser = create_main_parser()
    parsed_args = parser.parse_args(args)
    parsed_args.command = None
    
    # Show help if no arguments
    if parsed_args.filepath is None:
        parser.print_help()
        return 0
    
    # Set up observer
    observer = ConsoleProgressObserver(verbose=parsed_args.verbose)
    
    # Run CLI
    cli = SubtitleCLI(observer)
    return cli.run(parsed_args)


if __name__ == "__main__":
    sys.exit(main())
