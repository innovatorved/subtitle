"""Subtitle generation orchestration with VAD, presets, and multi-format export."""

from __future__ import annotations

import inspect
import logging
import os
import shutil
from typing import Callable, Optional

from ..models import ModelManager
from ..utils.file_handler import file_exists
from ..utils.formatters import SubtitleFormatterFactory
from ..utils.postprocess import reflow_segments, scrub_hallucinations
from .transcriber import TranscriberStrategy, TranscriptionResult, WhisperCppTranscriber

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """Coordinates model resolution, VAD, transcription, post-processing, and export."""

    def __init__(
        self,
        transcriber: TranscriberStrategy,
        model_manager: Optional[ModelManager] = None,
    ):
        self.transcriber = transcriber
        self.model_manager = model_manager or ModelManager()

    def _resolve_vad_model(self, vad: Optional[bool]) -> Optional[str]:
        if not isinstance(self.transcriber, WhisperCppTranscriber):
            return None
        effective_vad = self.transcriber.vad if vad is None else vad
        if not effective_vad:
            return None
        if self.transcriber.vad_model_path and os.path.isfile(self.transcriber.vad_model_path):
            return self.transcriber.vad_model_path
        caps = self.transcriber.get_capabilities()
        if not caps.get("vad"):
            return None
        try:
            return self.model_manager.get_vad_model()
        except Exception as e:
            logger.warning("Could not fetch Silero VAD model (%s); continuing without VAD.", e)
            return None

    def generate(
        self,
        input_path: str,
        model_name: str = "base",
        output_format: str = "vtt",
        output_dir: str = "data",
        progress_callback: Optional[Callable[[str, float], None]] = None,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        output_formats: Optional[list[str]] = None,
        vad: Optional[bool] = None,
        preset: Optional[str] = None,
        style: str = "clean",
        font: Optional[str] = None,
        font_size: Optional[int] = None,
        position: str = "bottom",
        word_timestamps: bool = False,
        diarize: bool = False,
        tinydiarize: bool = False,
        scrub: bool = False,
    ) -> TranscriptionResult:
        if not file_exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if progress_callback:
            progress_callback("preparing", 0.0)

        # Only download GGML model when using whisper.cpp (or custom strategy expecting a local file)
        from .backends import CloudTranscriber, FasterWhisperTranscriber

        if isinstance(self.transcriber, (FasterWhisperTranscriber, CloudTranscriber)):
            model_path = model_name
        else:
            try:
                model_path = self.model_manager.get_model(model_name)
                logger.info("Using model: %s", model_path)
            except Exception as e:
                raise ValueError(f"Failed to get model '{model_name}': {e}")

        vad_model_path = self._resolve_vad_model(vad)

        if progress_callback:
            progress_callback("preparing", 1.0)

        requested_formats = list(output_formats) if output_formats else [output_format]
        primary_format = requested_formats[0]

        transcribe_kwargs: dict = {
            "input_path": input_path,
            "model_path": model_path,
            "output_format": primary_format,
            "output_dir": output_dir,
            "progress_callback": progress_callback,
        }

        try:
            params = inspect.signature(self.transcriber.transcribe).parameters
            accepts_var_kw = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
            )
            optional_args = (
                ("language", language),
                ("translate", translate),
                ("max_len", max_len),
                ("split_on_word", split_on_word),
                ("prompt", prompt),
                ("output_formats", requested_formats),
                ("vad", vad),
                ("vad_model_path", vad_model_path),
                ("word_timestamps", word_timestamps or (style == "karaoke")),
                ("diarize", diarize),
                ("tinydiarize", tinydiarize),
                ("model_name", model_name),
            )
            for key, val in optional_args:
                if key in params or accepts_var_kw:
                    transcribe_kwargs[key] = val
        except (TypeError, ValueError):
            pass

        result = self.transcriber.transcribe(**transcribe_kwargs)

        if not result.success:
            logger.error("Transcription failed: %s", result.error)
            return result

        # Post-process (preset reflow / hallucination scrub) & render any derived formats (ass, ttml, etc.)
        existing_formats = (
            set(result.output_paths.keys()) if result.output_paths else {result.format}
        )
        needs_derived = any(fmt not in existing_formats for fmt in requested_formats)
        needs_postprocess = bool(preset) or scrub or needs_derived

        if needs_postprocess and os.path.isfile(result.output_path):
            orig_paths = dict(result.output_paths or {})
            # Prefer JSON source if available (preserves word timings & speakers)
            src_fmt = "json" if "json" in result.output_paths and os.path.isfile(result.output_paths["json"]) else result.format
            src_path = result.output_paths.get(src_fmt, result.output_path)
            try:
                parser = SubtitleFormatterFactory.create(src_fmt)
                with open(src_path, "r", encoding="utf-8") as f:
                    segments = parser.parse(f.read())

                if preset:
                    segments = reflow_segments(segments, preset_name=preset, scrub=True)
                elif scrub:
                    segments = scrub_hallucinations(segments)

                output_base = os.path.splitext(result.output_path)[0]
                new_paths: dict[str, str] = {}
                for fmt in requested_formats:
                    fmt_kwargs = (
                        {"style": style, "font": font, "font_size": font_size, "position": position}
                        if fmt == "ass"
                        else {}
                    )
                    formatter = SubtitleFormatterFactory.create(fmt, **fmt_kwargs)
                    dest = f"{output_base}.{formatter.file_extension}"
                    with open(dest, "w", encoding="utf-8") as f:
                        f.write(formatter.format(segments))
                    new_paths[fmt] = dest

                result.output_paths = new_paths
                result.output_path = new_paths[primary_format]
                result.format = primary_format

                # Clean up intermediate files that were not requested by the caller
                for orig_fmt, orig_path in list(orig_paths.items()):
                    if orig_fmt not in new_paths and os.path.isfile(orig_path):
                        try:
                            os.remove(orig_path)
                        except OSError:
                            pass
            except Exception as e:
                if needs_derived:
                    logger.error("Failed to generate requested format(s): %s", e)
                    return TranscriptionResult(
                        process_id=result.process_id,
                        input_path=result.input_path,
                        output_path="",
                        format=primary_format,
                        success=False,
                        error=f"Subtitle format conversion failed: {e}",
                    )
                logger.warning("Post-processing skipped (%s)", e)

        logger.info("Subtitles generated: %s", result.output_path)
        return result

    def generate_and_rename(
        self,
        input_path: str,
        model_name: str = "base",
        output_format: str = "vtt",
        output_dir: str = "data",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        language: Optional[str] = None,
        translate: bool = False,
        max_len: int = 0,
        split_on_word: bool = False,
        prompt: Optional[str] = None,
        output_formats: Optional[list[str]] = None,
        vad: Optional[bool] = None,
        preset: Optional[str] = None,
        style: str = "clean",
        font: Optional[str] = None,
        font_size: Optional[int] = None,
        position: str = "bottom",
        word_timestamps: bool = False,
        diarize: bool = False,
        tinydiarize: bool = False,
        scrub: bool = False,
    ) -> tuple[str, bool]:
        """Generate subtitles and move output to ``output_path``."""
        result = self.generate(
            input_path=input_path,
            model_name=model_name,
            output_format=output_format,
            output_dir=output_dir,
            progress_callback=progress_callback,
            language=language,
            translate=translate,
            max_len=max_len,
            split_on_word=split_on_word,
            prompt=prompt,
            output_formats=output_formats,
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

        if not result.success:
            return ("", False)

        if output_path:
            final_output_path = output_path
            target_base, _ = os.path.splitext(output_path)
        else:
            target_base, _ = os.path.splitext(input_path)
            final_output_path = f"{target_base}.{output_format}"

        # Move any additional multi-format outputs alongside the primary output
        extra_paths = {
            k: v for k, v in (result.output_paths or {}).items() if v != result.output_path
        }
        for fmt, src in extra_paths.items():
            if os.path.exists(src):
                dest = f"{target_base}.{fmt}"
                try:
                    dest_dir = os.path.dirname(dest)
                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)
                    if os.path.isfile(dest):
                        os.remove(dest)
                    shutil.move(src, dest)
                except OSError as e:
                    logger.warning("Failed to move extra format %s: %s", fmt, e)

        try:
            if os.path.exists(result.output_path):
                final_dir = os.path.dirname(final_output_path)
                if final_dir:
                    os.makedirs(final_dir, exist_ok=True)
                if os.path.isfile(final_output_path):
                    os.remove(final_output_path)
                shutil.move(result.output_path, final_output_path)
                logger.info("Renamed output to: %s", final_output_path)
                return (final_output_path, True)
        except OSError as e:
            logger.error("Failed to rename output: %s", e)
            return (result.output_path, True)

        return (result.output_path, True)
