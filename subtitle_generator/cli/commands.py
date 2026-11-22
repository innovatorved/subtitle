"""CLI for `subtitle ...` (transcribe, doctor, setup-whisper, models, batch, convert, lint, shift, translate, watch, config)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Optional

from .. import __version__
from ..core.backends import create_transcriber
from ..core.batch_processor import BatchProcessor
from ..core.subtitle_gen import SubtitleGenerator
from ..core.video_processor import VideoProcessor
from ..core.watcher import FolderWatcher
from ..models import ModelManager
from ..utils.config import get_config_default, load_config, write_default_config
from ..utils.doctor import format_diagnostics, run_diagnostics
from ..utils.downloader import download_file, is_url
from ..utils.exceptions import TranscriptionError
from ..utils.file_handler import directory_exists
from ..utils.formatters import convert_subtitle_file
from ..utils.paths import default_config_path, default_output_dir, default_threads
from ..utils.postprocess import PRESETS, lint_subtitle_file, shift_subtitle_file
from ..utils.translator import translate_subtitle_file
from ..utils.validators import (
    get_supported_formats,
    parse_output_formats,
    validate_media_path,
    validate_model_name,
    validate_output_format,
)

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure CLI logging only when invoked from the command line."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    else:
        root.setLevel(level)


# ============================================================================
# Observer Pattern for Progress Tracking
# ============================================================================


class ProgressObserver(ABC):
    """Abstract observer for progress updates."""

    @abstractmethod
    def on_progress(self, stage: str, progress: float, message: str = "") -> None:
        pass

    @abstractmethod
    def on_complete(self, success: bool, result: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def on_error(self, error: str) -> None:
        pass


class ConsoleProgressObserver(ProgressObserver):
    """Console-based progress observer with clean live progress output."""

    STAGE_LABELS = {
        "preparing": "[PREP]",
        "downloading": "[DOWN]",
        "transcribing": "[TRANS]",
        "merging": "[MERGE]",
        "burning": "[BURN]",
        "complete": "[DONE]",
        "error": "[ERROR]",
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def on_progress(self, stage: str, progress: float, message: str = "") -> None:
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

    def on_complete(self, success: bool, result: Optional[str] = None) -> None:
        if success:
            label = self.STAGE_LABELS["complete"]
            print(f"\n{label} Success!")
            if result:
                print(f"   Output: {result}")
        else:
            label = self.STAGE_LABELS["error"]
            print(f"\n{label} Failed")

    def on_error(self, error: str) -> None:
        label = self.STAGE_LABELS["error"]
        print(f"\n{label} Error: {error}", file=sys.stderr)


class SilentProgressObserver(ProgressObserver):
    """Silent observer that captures results without stdout noise (used for --json & tests)."""

    def __init__(self) -> None:
        self.stages: list[tuple[str, float, str]] = []
        self.errors: list[str] = []
        self.result: Optional[str] = None
        self.success: bool = False

    def on_progress(self, stage: str, progress: float, message: str = "") -> None:
        self.stages.append((stage, progress, message))

    def on_complete(self, success: bool, result: Optional[str] = None) -> None:
        self.success = success
        self.result = result

    def on_error(self, error: str) -> None:
        self.errors.append(error)


# ============================================================================
# CLI Class
# ============================================================================


class SubtitleCLI:
    """Command-line interface for subtitle generation and toolkit commands."""

    def __init__(
        self,
        observer: Optional[ProgressObserver] = None,
        models_dir: Optional[str] = None,
        whisper_binary: Optional[str] = None,
    ):
        self.observer = observer or ConsoleProgressObserver()
        self.whisper_binary = whisper_binary
        self.model_manager = ModelManager(models_dir=models_dir)

    def run(self, args: argparse.Namespace) -> int:
        try:
            cmd = getattr(args, "command", None)
            if cmd == "models":
                return self._handle_models_command(args)
            if cmd == "formats":
                return self._handle_formats_command()
            if cmd == "batch":
                return self._handle_batch_command(args)
            if cmd == "convert":
                return self._handle_convert_command(args)
            if cmd == "doctor":
                return self._handle_doctor_command(args)
            if cmd == "lint":
                return self._handle_lint_command(args)
            if cmd == "shift":
                return self._handle_shift_command(args)
            if cmd == "translate":
                return self._handle_translate_command(args)
            if cmd == "watch":
                return self._handle_watch_command(args)
            if cmd == "config":
                return self._handle_config_command(args)

            return self._handle_process_command(args)

        except KeyboardInterrupt:
            print("\n\nOperation cancelled.", file=sys.stderr)
            return 130
        except Exception as e:
            self.observer.on_error(str(e))
            logger.exception("Unexpected error")
            return 1

    def _emit_json(self, payload: dict[str, Any]) -> None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    def _handle_process_command(self, args: argparse.Namespace) -> int:
        filepath = args.filepath
        model = args.model
        format_spec = args.format
        merge = getattr(args, "merge", False)
        burn = getattr(args, "burn", False)
        language = getattr(args, "language", None)
        translate = getattr(args, "translate", False)
        max_len = getattr(args, "max_len", 0) or 0
        split_on_word = getattr(args, "split_on_word", False)
        prompt = getattr(args, "prompt", None)
        json_out = getattr(args, "json_output", False)

        if not filepath:
            self.observer.on_error("No video file specified")
            if json_out:
                self._emit_json({"success": False, "error": "No video file specified"})
            return 1

        temp_download_path: Optional[str] = None
        if is_url(filepath):
            self.observer.on_progress("downloading", 0.0)
            try:
                filepath = download_file(
                    filepath,
                    show_progress=not json_out,
                    output_dir=default_output_dir(),
                )
                temp_download_path = filepath
                self.observer.on_progress("downloading", 1.0)
            except Exception as e:
                self.observer.on_error(f"Download failed: {e}")
                if json_out:
                    self._emit_json({"success": False, "error": f"Download failed: {e}"})
                return 1

        try:
            return self._process_local_media(
                filepath=filepath,
                model=model,
                format_spec=format_spec,
                merge=merge,
                burn=burn,
                language=language,
                translate=translate,
                max_len=max_len,
                split_on_word=split_on_word,
                prompt=prompt,
                args=args,
            )
        finally:
            if temp_download_path and os.path.exists(temp_download_path):
                try:
                    os.remove(temp_download_path)
                except OSError:
                    pass

    def _process_local_media(
        self,
        *,
        filepath: str,
        model: str,
        format_spec: str,
        merge: bool,
        burn: bool,
        language: Optional[str],
        translate: bool,
        max_len: int,
        split_on_word: bool,
        prompt: Optional[str],
        args: argparse.Namespace,
    ) -> int:
        json_out = getattr(args, "json_output", False)
        backend = getattr(args, "backend", "whisper.cpp")
        vad = not getattr(args, "no_vad", False)
        preset = getattr(args, "preset", None)
        style = getattr(args, "style", "clean") or "clean"
        font = getattr(args, "font", None)
        font_size = getattr(args, "font_size", None)
        position = getattr(args, "position", "bottom") or "bottom"
        diarize = getattr(args, "diarize", False)
        tinydiarize = getattr(args, "tinydiarize", False)
        word_timestamps = getattr(args, "word_timestamps", False)
        scrub = getattr(args, "scrub", False)
        no_gpu = getattr(args, "no_gpu", False)
        beam_size = getattr(args, "beam_size", None)
        best_of = getattr(args, "best_of", None)
        carry_initial_prompt = getattr(args, "carry_initial_prompt", False)

        def _fail(msg: str) -> int:
            self.observer.on_error(msg)
            if json_out:
                self._emit_json({"success": False, "error": msg})
            return 1

        valid, error = validate_media_path(filepath)
        if not valid:
            return _fail(error or "Invalid media path")

        if backend == "whisper.cpp":
            valid, error = validate_model_name(model)
            if not valid:
                return _fail(error or "Invalid model")

        formats, err = parse_output_formats(format_spec)
        if err or not formats:
            return _fail(err or "Invalid format")
        primary_format = formats[0]

        if preset and preset.lower() not in PRESETS:
            return _fail(f"Unknown preset: {preset}. Available: {', '.join(sorted(PRESETS))}")

        try:
            transcriber = create_transcriber(
                backend=backend,
                binary_path=self.whisper_binary,
                threads=getattr(args, "threads", None),
                processors=getattr(args, "processors", 1),
                language=language,
                translate=translate,
                max_len=max_len,
                split_on_word=split_on_word,
                prompt=prompt,
                vad=vad,
                carry_initial_prompt=carry_initial_prompt,
                beam_size=beam_size,
                best_of=best_of,
                no_gpu=no_gpu,
                diarize=diarize,
                tinydiarize=tinydiarize,
                word_timestamps=word_timestamps or (style == "karaoke"),
            )
        except TranscriptionError as e:
            return _fail(str(e))

        generator = SubtitleGenerator(transcriber, self.model_manager)

        def progress_callback(stage: str, progress: float) -> None:
            self.observer.on_progress(stage, progress)

        target_dir = os.path.abspath(args.output_dir) if args.output_dir else os.getcwd()
        os.makedirs(target_dir, exist_ok=True)
        input_basename = os.path.splitext(os.path.basename(filepath))[0]
        final_subtitle_path = os.path.join(target_dir, f"{input_basename}.{primary_format}")

        subtitle_path, success = generator.generate_and_rename(
            input_path=filepath,
            model_name=model,
            output_format=primary_format,
            output_formats=formats,
            output_dir=default_output_dir(),
            output_path=final_subtitle_path,
            progress_callback=progress_callback,
            language=language,
            translate=translate,
            max_len=max_len,
            split_on_word=split_on_word,
            prompt=prompt,
            vad=vad,
            preset=preset,
            style=style,
            font=font,
            font_size=font_size,
            position=position,
            word_timestamps=word_timestamps,
            diarize=diarize,
            tinydiarize=tinydiarize,
            scrub=scrub,
        )

        if not success:
            return _fail("Transcription failed")

        final_result_path = subtitle_path

        if burn:
            self.observer.on_progress("burning", 0.0)
            processor = VideoProcessor()
            input_ext = os.path.splitext(filepath)[1] or ".mp4"
            burned_output_path = os.path.join(target_dir, f"{input_basename}_burned{input_ext}")

            def _burn_prog(p: float) -> None:
                self.observer.on_progress("burning", p)

            ok = processor.burn_subtitles(
                filepath,
                subtitle_path,
                burned_output_path,
                font_size=font_size,
                style=style,
                font=font,
                position=position,
                progress_callback=_burn_prog,
            )
            if not ok:
                return _fail("Failed to burn subtitles")
            self.observer.on_progress("burning", 1.0)
            final_result_path = burned_output_path
        elif merge:
            self.observer.on_progress("merging", 0.0)
            processor = VideoProcessor()
            input_ext = os.path.splitext(filepath)[1] or ".mp4"
            merged_output_path = os.path.join(target_dir, f"{input_basename}_subtitled{input_ext}")
            if not processor.merge_subtitles(filepath, subtitle_path, merged_output_path):
                return _fail("Failed to merge subtitles")
            self.observer.on_progress("merging", 1.0)
            final_result_path = merged_output_path

        self.observer.on_complete(True, final_result_path)
        if json_out:
            all_outputs = {
                fmt: os.path.join(target_dir, f"{input_basename}.{fmt}")
                for fmt in formats
                if os.path.exists(os.path.join(target_dir, f"{input_basename}.{fmt}"))
            }
            self._emit_json(
                {
                    "success": True,
                    "input": filepath,
                    "output": final_result_path,
                    "subtitles": all_outputs or {primary_format: subtitle_path},
                    "model": model,
                    "backend": backend,
                    "preset": preset,
                }
            )
        return 0

    def _handle_models_command(self, args: argparse.Namespace) -> int:
        if getattr(args, "list", False):
            available = self.model_manager.list_available_models()
            downloaded = self.model_manager.list_downloaded_models()
            print(f"Models directory: {self.model_manager.models_dir}")
            print("Available models:")
            for model in available:
                status = "x" if model in downloaded else " "
                print(f"  [{status}] {model}")
            print(f"\nDownloaded: {len(downloaded)}/{len(available)}")
            return 0

        if getattr(args, "download", None):
            model_name = args.download
            valid, error = validate_model_name(model_name)
            if not valid:
                self.observer.on_error(error or "Invalid model")
                return 1
            try:
                path = self.model_manager.download_model(model_name)
                print(f"Downloaded: {path}")
                return 0
            except Exception as e:
                self.observer.on_error(str(e))
                return 1

        return self._handle_models_command(argparse.Namespace(list=True, download=None))

    def _handle_formats_command(self) -> int:
        formats = get_supported_formats()
        print("Supported subtitle formats:")
        for fmt in formats:
            print(f"  - {fmt}")
        return 0

    def _handle_doctor_command(self, args: argparse.Namespace) -> int:
        report = run_diagnostics(
            whisper_binary=self.whisper_binary,
            models_dir=self.model_manager.models_dir,
        )
        if getattr(args, "json_output", False):
            self._emit_json(report)
        else:
            print(format_diagnostics(report))
        return 0 if report["healthy"] else 1

    def _handle_lint_command(self, args: argparse.Namespace) -> int:
        try:
            report = lint_subtitle_file(args.input_path, standard=args.standard)
        except Exception as e:
            self.observer.on_error(str(e))
            if getattr(args, "json_output", False):
                self._emit_json({"passed": False, "error": str(e)})
            return 1

        if getattr(args, "json_output", False):
            self._emit_json(report.to_dict())
        else:
            status = "PASS" if report.passed else "FAIL"
            print(
                f"[LINT] {status} ({report.standard}) — "
                f"{report.total_cues} cues, {len(report.issues)} issue(s)"
            )
            for issue in report.issues:
                print(f"  Cue #{issue.cue_index} [{issue.severity.upper()}:{issue.code}] {issue.message}")
        return 0 if report.passed else 1

    def _handle_shift_command(self, args: argparse.Namespace) -> int:
        try:
            written = shift_subtitle_file(
                input_path=args.input_path,
                offset_ms=args.offset,
                output_path=getattr(args, "output", None),
            )
            self.observer.on_complete(True, written)
            return 0
        except Exception as e:
            self.observer.on_error(str(e))
            return 1

    def _handle_translate_command(self, args: argparse.Namespace) -> int:
        try:
            written = translate_subtitle_file(
                input_path=args.input_path,
                target_lang=args.to,
                output_path=getattr(args, "output", None),
                source_lang=getattr(args, "source_lang", "auto"),
                provider=getattr(args, "provider", "auto"),
                model=getattr(args, "model", None),
            )
            self.observer.on_complete(True, written)
            return 0
        except Exception as e:
            self.observer.on_error(str(e))
            return 1

    def _handle_watch_command(self, args: argparse.Namespace) -> int:
        try:
            watcher = FolderWatcher(
                input_dir=args.input_dir,
                output_dir=getattr(args, "output_dir", None),
                model=args.model,
                output_format=args.format,
                poll_interval=args.interval,
                recursive=getattr(args, "recursive", False),
                whisper_binary=self.whisper_binary,
                models_dir=self.model_manager.models_dir,
                language=getattr(args, "language", None),
                translate=getattr(args, "translate", False),
                preset=getattr(args, "preset", None),
                vad=not getattr(args, "no_vad", False),
                backend=getattr(args, "backend", "whisper.cpp"),
                process_existing=getattr(args, "process_existing", False),
            )
            print(f"[WATCH] Watching {watcher.input_dir} -> {watcher.output_dir} (Ctrl+C to stop)")

            def _on_event(event: str, src: str, out: Optional[str]) -> None:
                name = os.path.basename(src)
                if event == "processing":
                    print(f"[WATCH] Detected new file: {name}")
                elif event == "complete":
                    print(f"[DONE]  {name} -> {out}")
                elif event == "error":
                    print(f"[ERROR] Failed: {name}", file=sys.stderr)

            watcher.run(on_event=_on_event)
            return 0
        except Exception as e:
            self.observer.on_error(str(e))
            return 1

    def _handle_config_command(self, args: argparse.Namespace) -> int:
        cfg_path = default_config_path()
        if getattr(args, "init", False):
            created = write_default_config(cfg_path, overwrite=getattr(args, "force", False))
            print(f"Config written to: {created}")
            return 0
        if getattr(args, "path", False):
            print(cfg_path)
            return 0
        cfg = load_config()
        print(f"Config path: {cfg_path}")
        print(json.dumps(cfg, indent=2))
        return 0

    def _handle_batch_command(self, args: argparse.Namespace) -> int:
        input_dir = args.input_dir
        output_dir = args.output_dir or input_dir
        workers = args.workers
        model = args.model
        output_format = args.format
        resume = args.resume
        extensions = args.extensions.split(",") if args.extensions else None
        language = getattr(args, "language", None)
        translate = getattr(args, "translate", False)
        max_len = getattr(args, "max_len", 0) or 0
        split_on_word = getattr(args, "split_on_word", False)
        prompt = getattr(args, "prompt", None)
        recursive = getattr(args, "recursive", False)
        vad = not getattr(args, "no_vad", False)
        preset = getattr(args, "preset", None)
        merge = getattr(args, "merge", False)
        burn = getattr(args, "burn", False)
        style = getattr(args, "style", "clean") or "clean"
        backend = getattr(args, "backend", "whisper.cpp")

        if not directory_exists(input_dir):
            self.observer.on_error(f"Input directory does not exist: {input_dir}")
            return 1

        if backend == "whisper.cpp":
            valid, error = validate_model_name(model)
            if not valid:
                self.observer.on_error(error or "Invalid model")
                return 1

        valid, error = validate_output_format(output_format)
        if not valid:
            self.observer.on_error(error or "Invalid format")
            return 1

        processor = BatchProcessor(
            workers=workers,
            model=model,
            output_format=output_format,
            extensions=extensions,
            whisper_binary=self.whisper_binary,
            models_dir=self.model_manager.models_dir,
            language=language,
            translate=translate,
            max_len=max_len,
            split_on_word=split_on_word,
            prompt=prompt,
            threads=getattr(args, "threads", None),
            processors=getattr(args, "processors", 1),
            recursive=recursive,
            vad=vad,
            preset=preset,
            merge=merge,
            burn=burn,
            style=style,
            backend=backend,
        )

        video_files = processor.find_video_files(input_dir)
        if not video_files:
            print(f"No media files found in {input_dir}")
            return 0

        print(f"Found {len(video_files)} media files")
        print(f"Output directory: {output_dir}")
        print(f"Model: {model}, Format: {output_format}, Workers: {workers}, Threads/worker: {processor.threads}")
        if resume:
            print("Resume mode: enabled")
        print()

        def progress_callback(file_path: str, current: int, total: int, status: str) -> None:
            filename = os.path.basename(file_path)
            print(f"[{current}/{total}] {filename}: {status}")

        try:
            summary = processor.process_batch(
                input_dir=input_dir,
                output_dir=output_dir,
                resume=resume,
                progress_callback=progress_callback,
            )

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
            report_file = os.path.join(output_dir, BatchProcessor.REPORT_FILE_NAME)
            print(f"Report saved to: {report_file}")

            return 0 if summary.failed == 0 else 1
        except Exception as e:
            self.observer.on_error(str(e))
            return 1

    def _handle_convert_command(self, args: argparse.Namespace) -> int:
        try:
            kwargs: dict[str, Any] = {}
            if getattr(args, "style", None):
                kwargs["style"] = args.style
            written = convert_subtitle_file(
                input_path=args.input_path,
                output_path=getattr(args, "output_path", None),
                target_format=getattr(args, "format", None),
                source_format=getattr(args, "source_format", None),
                **kwargs,
            )
            self.observer.on_complete(True, written)
            return 0
        except Exception as e:
            self.observer.on_error(str(e))
            return 1


# ============================================================================
# Argument Parsers
# ============================================================================


def create_main_parser(config: Optional[dict[str, Any]] = None) -> argparse.ArgumentParser:
    cfg = config or {}
    parser = argparse.ArgumentParser(
        prog="subtitle",
        description="Industry-standard AI subtitle generation, styling, QC, and embedding toolkit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subcommands:
  subtitle setup-whisper                Install prebuilt (or compile) whisper-cli
  subtitle doctor                       Check OS, GPU, whisper-cli, ffmpeg & extras
  subtitle models --list                List / download Whisper models
  subtitle batch -i ./videos -o ./subs  Parallel batch processing (video & audio)
  subtitle watch ./incoming -o ./subs   Auto-subtitle new files dropped in a folder
  subtitle convert in.vtt out.ass       Convert between vtt, srt, ass, ttml, json, csv, lrc, txt
  subtitle lint subs.srt                Validate CPL/CPS/timing (netflix, bbc, reels)
  subtitle shift subs.srt --offset 500  Shift subtitle timestamps (+/- ms)
  subtitle translate subs.srt --to es   Translate subtitle file preserving timestamps
  subtitle config --init                Create ~/.config/subtitle-generator/config.toml
  subtitle formats                      List supported subtitle formats

Examples:
  subtitle video.mp4 --format srt,vtt,ass --preset netflix
  subtitle reel.mp4 --burn --style karaoke --preset reels
  subtitle https://youtu.be/dQw4w9WgXcQ --model turbo --format srt
        """,
    )

    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("filepath", type=str, nargs="?", default=None, help="Path to video/audio file or URL")
    parser.add_argument("--model", "-m", type=str, default=get_config_default(cfg, "model", "base"), help="Whisper model (default: base)")
    parser.add_argument("--format", "-f", type=str, default=get_config_default(cfg, "format", "vtt"), help="Output format(s), comma-separated e.g. srt,vtt,ass (default: vtt)")
    parser.add_argument("--backend", type=str, default=get_config_default(cfg, "backend", "whisper.cpp"), help="Transcription backend: whisper.cpp, faster-whisper, openai, groq")
    parser.add_argument("--language", "-l", type=str, default=get_config_default(cfg, "language", None), help="Spoken language code (e.g. 'en', 'es', 'auto')")
    parser.add_argument("--translate", "-tr", action="store_true", help="Translate speech to English")
    parser.add_argument("--preset", type=str, default=get_config_default(cfg, "preset", None), help="Broadcast/creator reflow preset: netflix, netflix-kids, bbc, reels, shorts")
    vad_group = parser.add_mutually_exclusive_group()
    vad_group.add_argument("--vad", dest="no_vad", action="store_false", help="Enable Silero VAD voice activity detection (default)")
    vad_group.add_argument("--no-vad", dest="no_vad", action="store_true", help="Disable Silero VAD voice activity detection")
    parser.set_defaults(no_vad=not get_config_default(cfg, "vad", True))
    parser.add_argument("--diarize", action="store_true", help="Enable stereo audio speaker diarization (-di)")
    parser.add_argument("--tinydiarize", "-tdrz", action="store_true", help="Enable TinyDiarize speaker turns (requires tdrz model)")
    parser.add_argument("--word-timestamps", action="store_true", help="Preserve word-level timestamps in JSON/ASS")
    parser.add_argument("--scrub", action="store_true", help="Scrub Whisper repetition/silence hallucinations")
    parser.add_argument("--max-len", "-ml", type=int, default=0, metavar="N", help="Maximum segment length in characters")
    parser.add_argument("--split-on-word", "-sow", action="store_true", help="Split segments on word boundaries")
    parser.add_argument("--prompt", type=str, default=None, metavar="TEXT", help="Initial prompt guiding vocabulary/names")
    parser.add_argument("--carry-initial-prompt", action="store_true", help="Carry initial prompt across all audio windows")
    parser.add_argument("--beam-size", type=int, default=None, help="Beam search size")
    parser.add_argument("--best-of", type=int, default=None, help="Number of best candidates to keep")
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU execution")

    embed_group = parser.add_mutually_exclusive_group()
    embed_group.add_argument("--merge", action="store_true", help="Mux soft subtitles into video copy")
    embed_group.add_argument("--burn", action="store_true", help="Burn (hardcode) styled subtitles into video")

    parser.add_argument("--style", type=str, default=get_config_default(cfg, "style", "clean", section="burn"), help="ASS/burn caption style: clean, box, karaoke, cinema")
    parser.add_argument("--font", type=str, default=get_config_default(cfg, "font", None, section="burn"), help="Font family for burned/ASS captions")
    parser.add_argument("--font-size", type=int, default=get_config_default(cfg, "font_size", None, section="burn"), help="Font size override for burned/ASS captions")
    parser.add_argument("--position", type=str, default=get_config_default(cfg, "position", "bottom", section="burn"), help="Caption vertical position: bottom, center, top")

    parser.add_argument("--threads", "-t", type=int, default=get_config_default(cfg, "threads", default_threads()), help="CPU threads (default: auto)")
    parser.add_argument("--processors", "-p", type=int, default=1, help="Number of processors (default: 1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit machine-readable JSON output")
    parser.add_argument("--output-dir", "-o", type=str, default=None, metavar="DIR", help="Output directory (default: CWD)")
    parser.add_argument("--whisper-binary", type=str, default=get_config_default(cfg, "whisper_binary", None), metavar="PATH", help="Path to whisper-cli")
    parser.add_argument("--models-dir", type=str, default=get_config_default(cfg, "models_dir", None), metavar="DIR", help="Model cache directory")
    return parser


def create_models_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle models", description="Manage Whisper models")
    parser.add_argument("--list", "-l", action="store_true", help="List available models")
    parser.add_argument("--download", "-d", type=str, metavar="MODEL", help="Download a model")
    parser.add_argument("--models-dir", type=str, default=None, metavar="DIR", help="Model cache directory")
    return parser


def create_setup_whisper_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subtitle setup-whisper",
        description="Install prebuilt whisper-cli binary (or build from source as fallback).",
    )
    parser.add_argument("--from-source", action="store_true", help="Skip prebuilt binary and compile from source")
    parser.add_argument("--gpu", type=str, default="auto", choices=["auto", "metal", "cuda", "vulkan", "cpu"], help="GPU backend for source builds (default: auto)")
    parser.add_argument("--repo", type=str, default=None, metavar="URL", help="Override default fork URL")
    parser.add_argument("--ref", type=str, default=None, metavar="REF", help="Branch, tag, or commit (default: develop)")
    parser.add_argument("--force", action="store_true", help="Wipe and re-clone source tree")
    parser.add_argument("--no-pull", action="store_true", help="Skip git fetch/pull (offline rebuild)")
    return parser


def create_batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle batch", description="Batch process media files in parallel")
    parser.add_argument("--input-dir", "-i", type=str, required=True, help="Directory containing media files")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Directory for output (default: same as input)")
    parser.add_argument("--recursive", "-R", action="store_true", help="Search subdirectories recursively")
    parser.add_argument("--workers", "-w", type=int, default=2, help="Parallel workers (default: 2)")
    parser.add_argument("--model", "-m", type=str, default="base", help="Whisper model (default: base)")
    parser.add_argument("--format", "-f", type=str, default="vtt", help="Output subtitle format (default: vtt)")
    parser.add_argument("--backend", type=str, default="whisper.cpp", help="Transcription backend")
    parser.add_argument("--language", "-l", type=str, default=None, help="Spoken language code")
    parser.add_argument("--translate", "-tr", action="store_true", help="Translate speech to English")
    parser.add_argument("--preset", type=str, default=None, help="Broadcast/creator preset (netflix, bbc, reels)")
    parser.add_argument("--no-vad", action="store_true", help="Disable Silero VAD")
    parser.add_argument("--max-len", "-ml", type=int, default=0, metavar="N", help="Maximum segment length")
    parser.add_argument("--split-on-word", "-sow", action="store_true", help="Split on word boundaries")
    parser.add_argument("--prompt", type=str, default=None, metavar="TEXT", help="Initial prompt")
    embed_group = parser.add_mutually_exclusive_group()
    embed_group.add_argument("--merge", action="store_true", help="Mux soft subtitles into video copies")
    embed_group.add_argument("--burn", action="store_true", help="Burn subtitles into video copies")
    parser.add_argument("--style", type=str, default="clean", help="Style for burned/ASS subtitles")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume interrupted batch")
    parser.add_argument("--extensions", "-e", type=str, default=None, help="Comma-separated extensions")
    parser.add_argument("--threads", "-t", type=int, default=None, help="Threads per worker (default: auto)")
    parser.add_argument("--processors", "-p", type=int, default=1, help="Processors per worker")
    parser.add_argument("--whisper-binary", type=str, default=None, metavar="PATH", help="Path to whisper-cli")
    parser.add_argument("--models-dir", type=str, default=None, metavar="DIR", help="Model cache directory")
    return parser


def create_convert_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subtitle convert",
        description="Convert subtitle files between vtt, srt, ass, ttml, json, csv, lrc, txt",
    )
    parser.add_argument("input_path", type=str, help="Source subtitle file")
    parser.add_argument("output_path", type=str, nargs="?", default=None, help="Destination path")
    parser.add_argument("--format", "-f", type=str, default=None, help="Target format")
    parser.add_argument("--source-format", type=str, default=None, help="Explicit source format")
    parser.add_argument("--style", type=str, default=None, help="ASS style preset (clean, box, karaoke, cinema)")
    return parser


def create_doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle doctor", description="Diagnose OS, GPU, whisper-cli, ffmpeg & extras")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output JSON diagnostics")
    parser.add_argument("--whisper-binary", type=str, default=None, metavar="PATH")
    parser.add_argument("--models-dir", type=str, default=None, metavar="DIR")
    return parser


def create_lint_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle lint", description="Validate subtitle timing & readability against industry standards")
    parser.add_argument("input_path", type=str, help="Subtitle file to validate")
    parser.add_argument("--standard", "-s", type=str, default="netflix", help="Standard: netflix, netflix-kids, bbc, reels, shorts")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output JSON report")
    return parser


def create_shift_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle shift", description="Shift subtitle timestamps by +/- milliseconds")
    parser.add_argument("input_path", type=str, help="Subtitle file to shift")
    parser.add_argument("--offset", type=int, required=True, help="Offset in milliseconds (e.g. 500 or -250)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file (default: overwrite in place)")
    return parser


def create_translate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle translate", description="Translate a subtitle file while preserving timestamps")
    parser.add_argument("input_path", type=str, help="Source subtitle file")
    parser.add_argument("--to", required=True, type=str, help="Target language code (e.g. es, fr, de, ja, hi)")
    parser.add_argument("--from", dest="source_lang", default="auto", type=str, help="Source language code (default: auto)")
    parser.add_argument("--provider", default="auto", choices=["auto", "argos", "openai", "groq"], help="Translation provider")
    parser.add_argument("--model", default=None, type=str, help="Optional LLM model override")
    parser.add_argument("--output", "-o", default=None, type=str, help="Destination path")
    return parser


def create_watch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle watch", description="Watch a directory and auto-subtitle new media files")
    parser.add_argument("input_dir", type=str, help="Directory to watch")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Output directory")
    parser.add_argument("--model", "-m", type=str, default="base")
    parser.add_argument("--format", "-f", type=str, default="vtt")
    parser.add_argument("--backend", type=str, default="whisper.cpp")
    parser.add_argument("--language", "-l", type=str, default=None)
    parser.add_argument("--translate", "-tr", action="store_true")
    parser.add_argument("--preset", type=str, default=None)
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument("--recursive", "-R", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("--process-existing", action="store_true", help="Also process files already in directory")
    parser.add_argument("--whisper-binary", type=str, default=None)
    parser.add_argument("--models-dir", type=str, default=None)
    return parser


def create_config_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subtitle config", description="Manage ~/.config/subtitle-generator/config.toml")
    parser.add_argument("--init", action="store_true", help="Write starter config.toml")
    parser.add_argument("--force", action="store_true", help="Overwrite existing config.toml with --init")
    parser.add_argument("--path", action="store_true", help="Print config file path")
    return parser


def _handle_setup_whisper_command(args: argparse.Namespace) -> int:
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
    from_source = bool(getattr(args, "from_source", False))
    gpu = getattr(args, "gpu", "auto") or "auto"

    def _stream(line: str) -> None:
        print(line, flush=True)

    try:
        result = setup_whisper(
            repo_url=repo,
            ref=ref,
            force=force,
            pull=pull,
            from_source=from_source,
            gpu=gpu,
            log_callback=_stream,
        )
    except WhisperSetupError as e:
        print(f"\n[ERROR] setup-whisper failed: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.", file=sys.stderr)
        return 130

    print(
        f"\n[DONE] whisper-cli installed at {result.binary_path} ({result.method})\n"
        "Run `subtitle doctor` to verify or `subtitle <video>` from anywhere."
    )
    return 0


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for CLI."""
    if args is None:
        args = sys.argv[1:]

    json_mode = "--json" in args
    _configure_logging(verbose="-v" in args or "--verbose" in args, quiet=json_mode)

    if args and args[0] == "models":
        parsed_args = create_models_parser().parse_args(args[1:])
        parsed_args.command = "models"
        cli = SubtitleCLI(ConsoleProgressObserver(), models_dir=parsed_args.models_dir)
        return cli.run(parsed_args)

    if args and args[0] == "formats":
        argparse.ArgumentParser(
            prog="subtitle formats", description="List supported subtitle output formats"
        ).parse_args(args[1:])
        return SubtitleCLI()._handle_formats_command()

    if args and args[0] == "setup-whisper":
        parsed_args = create_setup_whisper_parser().parse_args(args[1:])
        return _handle_setup_whisper_command(parsed_args)

    if args and args[0] == "doctor":
        parsed_args = create_doctor_parser().parse_args(args[1:])
        parsed_args.command = "doctor"
        cli = SubtitleCLI(
            SilentProgressObserver() if parsed_args.json_output else ConsoleProgressObserver(),
            models_dir=parsed_args.models_dir,
            whisper_binary=parsed_args.whisper_binary,
        )
        return cli.run(parsed_args)

    if args and args[0] == "batch":
        parsed_args = create_batch_parser().parse_args(args[1:])
        parsed_args.command = "batch"
        cli = SubtitleCLI(
            ConsoleProgressObserver(),
            models_dir=parsed_args.models_dir,
            whisper_binary=parsed_args.whisper_binary,
        )
        return cli.run(parsed_args)

    if args and args[0] == "convert":
        parsed_args = create_convert_parser().parse_args(args[1:])
        parsed_args.command = "convert"
        return SubtitleCLI(ConsoleProgressObserver()).run(parsed_args)

    if args and args[0] == "lint":
        parsed_args = create_lint_parser().parse_args(args[1:])
        parsed_args.command = "lint"
        obs: ProgressObserver = SilentProgressObserver() if parsed_args.json_output else ConsoleProgressObserver()
        return SubtitleCLI(obs).run(parsed_args)

    if args and args[0] == "shift":
        parsed_args = create_shift_parser().parse_args(args[1:])
        parsed_args.command = "shift"
        return SubtitleCLI(ConsoleProgressObserver()).run(parsed_args)

    if args and args[0] == "translate":
        parsed_args = create_translate_parser().parse_args(args[1:])
        parsed_args.command = "translate"
        return SubtitleCLI(ConsoleProgressObserver()).run(parsed_args)

    if args and args[0] == "watch":
        parsed_args = create_watch_parser().parse_args(args[1:])
        parsed_args.command = "watch"
        cli = SubtitleCLI(
            ConsoleProgressObserver(),
            models_dir=parsed_args.models_dir,
            whisper_binary=parsed_args.whisper_binary,
        )
        return cli.run(parsed_args)

    if args and args[0] == "config":
        parsed_args = create_config_parser().parse_args(args[1:])
        parsed_args.command = "config"
        return SubtitleCLI(ConsoleProgressObserver()).run(parsed_args)

    cfg = load_config()
    parser = create_main_parser(cfg)
    parsed_args = parser.parse_args(args)
    parsed_args.command = None

    if parsed_args.filepath is None:
        parser.print_help()
        return 0

    observer: ProgressObserver = (
        SilentProgressObserver()
        if parsed_args.json_output
        else ConsoleProgressObserver(verbose=parsed_args.verbose)
    )
    cli = SubtitleCLI(
        observer,
        models_dir=parsed_args.models_dir,
        whisper_binary=parsed_args.whisper_binary,
    )
    return cli.run(parsed_args)


if __name__ == "__main__":
    sys.exit(main())
