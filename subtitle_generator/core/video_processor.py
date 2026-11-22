"""Cross-platform video processor powered directly by FFmpeg/FFprobe subprocesses.

Eliminates the unmaintained ``ffmpeg-python`` dependency, supports optional
``imageio-ffmpeg`` static binary fallback, Windows-safe libavfilter path
escaping, hardware H.264 encoder auto-detection, and live progress reporting.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from ..utils.file_handler import file_exists, get_file_extension
from ..utils.formatters import ASSFormatter, SubtitleFormatterFactory
from ..utils.paths import find_ffmpeg_binary, find_ffprobe_binary

logger = logging.getLogger(__name__)


def _parse_frame_rate(rate_str: Optional[str]) -> float:
    """Safely parse FFmpeg rational frame rate string (e.g. '30000/1001')."""
    if not rate_str:
        return 0.0
    try:
        if "/" in str(rate_str):
            num_str, den_str = str(rate_str).split("/", 1)
            den = float(den_str)
            return float(num_str) / den if den != 0 else 0.0
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def escape_ffmpeg_filter_path(path: str) -> str:
    """Escape a filesystem path for FFmpeg's libavfilter ``subtitles`` / ``ass`` filter.

    Handles Windows drive letters (``C:/foo`` -> ``C\\:/foo``), quotes,
    brackets, and colons safely across macOS, Linux, and Windows.
    """
    abs_path = os.path.abspath(path)
    # Normalize to forward slashes first so Windows backslashes never clash
    posix = Path(abs_path).as_posix()
    return (
        posix.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


class VideoProcessor:
    """Handles FFmpeg/FFprobe video & audio operations cleanly across all OSes."""

    _CONTAINER_SUBTITLE_CODECS = {
        "mp4": "mov_text",
        "m4v": "mov_text",
        "mov": "mov_text",
        "mkv": "srt",
        "webm": "webvtt",
    }

    _hw_encoder_cache: dict[str, Optional[str]] = {}

    def __init__(
        self,
        overwrite_output: bool = True,
        ffmpeg_binary: Optional[str] = None,
        ffprobe_binary: Optional[str] = None,
    ):
        self.overwrite_output = overwrite_output
        self._explicit_ffmpeg = ffmpeg_binary
        self._explicit_ffprobe = ffprobe_binary

    def _ffmpeg(self) -> str:
        resolved = find_ffmpeg_binary(self._explicit_ffmpeg)
        if not resolved:
            raise RuntimeError(
                "FFmpeg binary not found on PATH. Install ffmpeg or run "
                "`pip install 'subtitle-generator[ffmpeg]'`."
            )
        return resolved

    def _ffprobe(self) -> Optional[str]:
        return find_ffprobe_binary(self._explicit_ffprobe)

    def _detect_hw_encoder(self, ffmpeg_bin: str) -> Optional[str]:
        """Auto-detect a fast hardware H.264 encoder when available."""
        if ffmpeg_bin in self._hw_encoder_cache:
            return self._hw_encoder_cache[ffmpeg_bin]
        try:
            proc = subprocess.run(
                [ffmpeg_bin, "-hide_banner", "-encoders"],
                check=False,
                capture_output=True,
                timeout=5,
            )
            out = (proc.stdout or b"").decode("utf-8", errors="replace")
            for candidate in ("h264_videotoolbox", "h264_nvenc", "h264_qsv"):
                if candidate in out:
                    self._hw_encoder_cache[ffmpeg_bin] = candidate
                    return candidate
        except Exception:
            pass
        self._hw_encoder_cache[ffmpeg_bin] = None
        return None

    def _run_ffmpeg(
        self,
        args: list[str],
        duration_sec: float = 0.0,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        ffmpeg_bin = self._ffmpeg()
        cmd = [ffmpeg_bin, "-hide_banner", "-loglevel", "error"]
        if self.overwrite_output:
            cmd.append("-y")
        else:
            cmd.append("-n")

        if progress_callback and duration_sec > 0:
            cmd.extend(["-progress", "pipe:1", "-nostats"])

        cmd.extend(args)

        if not (progress_callback and duration_sec > 0):
            completed = subprocess.run(cmd, check=False, capture_output=True)
            if completed.returncode != 0:
                err = (completed.stderr or completed.stdout or b"").decode("utf-8", errors="replace").strip()
                raise RuntimeError(err or f"FFmpeg exited with code {completed.returncode}")
            return

        import threading

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stderr_chunks: list[str] = []

        def _drain_stderr() -> None:
            try:
                if proc.stderr:
                    for line in proc.stderr:
                        if len(stderr_chunks) < 500:
                            stderr_chunks.append(line)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_us="):
                    try:
                        us = int(line.split("=", 1)[1])
                        pct = min(0.99, max(0.0, (us / 1_000_000.0) / duration_sec))
                        progress_callback(pct)
                    except ValueError:
                        pass
                elif line == "progress=end":
                    progress_callback(1.0)
            ret = proc.wait()
            stderr_thread.join(timeout=2)
            if ret != 0:
                stderr_text = "".join(stderr_chunks).strip()
                raise RuntimeError(stderr_text or f"FFmpeg exited with code {ret}")
        except BaseException:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            raise
        finally:
            for stream in (proc.stdout, proc.stderr):
                if stream and hasattr(stream, "close"):
                    try:
                        stream.close()
                    except OSError:
                        pass

    def merge_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        subtitle_codec: Optional[str] = None,
    ) -> bool:
        """Mux a soft subtitle track into a copy of the video (stream-copy, instant)."""
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not file_exists(subtitle_path):
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        if subtitle_codec is None:
            ext = get_file_extension(output_path)
            subtitle_codec = self._CONTAINER_SUBTITLE_CODECS.get(ext, "mov_text")

        try:
            logger.info("Merging subtitles: %s + %s", video_path, subtitle_path)
            self._run_ffmpeg(
                [
                    "-i", video_path,
                    "-i", subtitle_path,
                    "-map", "0",
                    "-map", "1",
                    "-c:v", "copy",
                    "-c:a", "copy",
                    "-c:s", subtitle_codec,
                    output_path,
                ]
            )
            logger.info("Successfully created: %s", output_path)
            return True
        except Exception as e:
            logger.error("Failed to merge subtitles: %s", e)
            return False

    def _has_audio_stream(self, video_path: str) -> bool:
        try:
            info = self.get_video_info(video_path)
            return "audio_codec" in info
        except Exception:
            return False

    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        font_size: Optional[int] = None,
        style: Optional[str] = None,
        font: Optional[str] = None,
        position: str = "bottom",
        use_hw_encoder: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Burn (hardcode) subtitles into video while preserving original audio."""
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not file_exists(subtitle_path):
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        temp_ass_path: Optional[str] = None
        try:
            logger.info("Burning subtitles into video: %s", video_path)
            sub_ext = get_file_extension(subtitle_path)

            # If a creator style preset or font/position is requested on non-ASS input,
            # render a styled temporary .ass file for consistent cross-platform output.
            if style and sub_ext != "ass":
                src_fmt = SubtitleFormatterFactory.create(sub_ext)
                with open(subtitle_path, "r", encoding="utf-8") as f:
                    segments = src_fmt.parse(f.read())
                ass_fmt = ASSFormatter(
                    style=style,
                    font=font,
                    font_size=font_size,
                    position=position,
                )
                fd, temp_ass_path = tempfile.mkstemp(prefix="sg_burn_", suffix=".ass")
                os.close(fd)
                with open(temp_ass_path, "w", encoding="utf-8") as f:
                    f.write(ass_fmt.format(segments))
                effective_sub = temp_ass_path
                sub_ext = "ass"
            else:
                effective_sub = subtitle_path

            escaped_path = escape_ffmpeg_filter_path(effective_sub)
            if sub_ext == "ass":
                vf_expr = f"ass={escaped_path}"
            else:
                eff_size = font_size if font_size is not None else 24
                style_parts = [f"FontSize={eff_size}"]
                if font:
                    safe_font = "".join(c for c in font if c not in "',:;\\")
                    if safe_font:
                        style_parts.append(f"FontName={safe_font}")
                align_map = {"bottom": 2, "center": 5, "top": 8}
                if position in align_map:
                    style_parts.append(f"Alignment={align_map[position]}")
                vf_expr = f"subtitles={escaped_path}:force_style='{','.join(style_parts)}'"

            duration = 0.0
            has_audio = False
            try:
                info = self.get_video_info(video_path)
                duration = float(info.get("duration", 0.0) or 0.0)
                has_audio = "audio_codec" in info
            except Exception:
                pass

            def _build_args(vcodec_args: list[str]) -> list[str]:
                args = ["-i", video_path, "-vf", vf_expr, *vcodec_args]
                if has_audio:
                    args.extend(["-c:a", "copy"])
                args.append(output_path)
                return args

            hw_enc = self._detect_hw_encoder(self._ffmpeg()) if use_hw_encoder else None
            if hw_enc:
                try:
                    self._run_ffmpeg(
                        _build_args(["-c:v", hw_enc, "-b:v", "6M", "-pix_fmt", "yuv420p"]),
                        duration_sec=duration,
                        progress_callback=progress_callback,
                    )
                    logger.info("Successfully burned subtitles (%s): %s", hw_enc, output_path)
                    return True
                except Exception as hw_err:
                    logger.warning("Hardware encoder %s failed (%s); falling back to libx264", hw_enc, hw_err)

            self._run_ffmpeg(
                _build_args(["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"]),
                duration_sec=duration,
                progress_callback=progress_callback,
            )
            logger.info("Successfully burned subtitles: %s", output_path)
            return True

        except Exception as e:
            logger.error("Failed to burn subtitles: %s", e)
            return False
        finally:
            if temp_ass_path and os.path.exists(temp_ass_path):
                try:
                    os.remove(temp_ass_path)
                except OSError:
                    pass

    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        audio_format: str = "wav",
        sample_rate: int = 16000,
    ) -> str:
        """Extract 16 kHz mono audio from a video/audio file using FFmpeg."""
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_path is None:
            base, _ = os.path.splitext(video_path)
            output_path = f"{base}.{audio_format}"

        try:
            logger.info("Extracting audio from: %s", video_path)
            args = [
                "-i", video_path,
                "-vn",
                "-ar", str(sample_rate),
                "-ac", "1",
            ]
            if audio_format == "wav":
                args.extend(["-c:a", "pcm_s16le"])
            args.append(output_path)

            self._run_ffmpeg(args)
            logger.info("Audio extracted to: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("FFmpeg audio extraction error: %s", e)
            raise RuntimeError(f"Failed to extract audio: {e}")

    def get_video_info(self, video_path: str) -> dict:
        """Probe video/audio metadata using ffprobe."""
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        ffprobe_bin = self._ffprobe()
        if not ffprobe_bin:
            raise RuntimeError("ffprobe binary not found on PATH.")

        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path,
            ],
            check=False,
            capture_output=True,
            timeout=15,
        )
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Failed to get video info: {err}")

        probe = json.loads((proc.stdout or b"{}").decode("utf-8", errors="replace"))
        streams = probe.get("streams", [])
        fmt = probe.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        info: dict = {
            "duration": float(fmt.get("duration", 0) or 0),
            "size_bytes": int(fmt.get("size", 0) or 0),
            "format": fmt.get("format_name", "unknown"),
        }
        if video_stream:
            info["width"] = video_stream.get("width")
            info["height"] = video_stream.get("height")
            info["video_codec"] = video_stream.get("codec_name")
            info["fps"] = _parse_frame_rate(video_stream.get("r_frame_rate", "0/1"))
        if audio_stream:
            info["audio_codec"] = audio_stream.get("codec_name")
            info["sample_rate"] = int(audio_stream.get("sample_rate", 0) or 0)
        return info
