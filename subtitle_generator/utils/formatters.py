"""
Subtitle format converters with Factory pattern.

Provides formatters for different subtitle formats (VTT, SRT, etc.)
with a factory for creating the appropriate formatter.
"""

import csv
import io
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SubtitleSegment:
    """Represents a single subtitle segment."""
    
    index: int
    start_time: float  # seconds
    end_time: float    # seconds
    text: str
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time


class SubtitleFormatter(ABC):
    """Abstract base class for subtitle formatters."""
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the format name."""
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for this format."""
        pass
    
    @abstractmethod
    def format(self, segments: list[SubtitleSegment]) -> str:
        """
        Format subtitle segments into a string.
        
        Args:
            segments: List of subtitle segments
            
        Returns:
            Formatted subtitle string
        """
        pass
    
    @abstractmethod
    def parse(self, content: str) -> list[SubtitleSegment]:
        """
        Parse subtitle content into segments.
        
        Args:
            content: Raw subtitle file content
            
        Returns:
            List of parsed subtitle segments
        """
        pass


class VTTFormatter(SubtitleFormatter):
    """WebVTT subtitle formatter."""
    
    @property
    def format_name(self) -> str:
        return "WebVTT"
    
    @property
    def file_extension(self) -> str:
        return "vtt"
    
    def format(self, segments: list[SubtitleSegment]) -> str:
        """Format segments to WebVTT format."""
        lines = ["WEBVTT", ""]
        
        for segment in segments:
            start = self._format_timestamp(segment.start_time)
            end = self._format_timestamp(segment.end_time)
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        
        return "\n".join(lines)
    
    def parse(self, content: str) -> list[SubtitleSegment]:
        """Parse WebVTT content into segments."""
        segments = []
        lines = content.strip().split("\n")
        
        # Skip WEBVTT header
        i = 0
        while i < len(lines) and not "-->" in lines[i]:
            i += 1
        
        index = 1
        while i < len(lines):
            line = lines[i].strip()
            
            if "-->" in line:
                # Parse timestamp line
                match = re.match(
                    r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})",
                    line
                )
                if match:
                    start = self._parse_timestamp(match.group(1))
                    end = self._parse_timestamp(match.group(2))
                    
                    # Collect text lines until empty line
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    segments.append(SubtitleSegment(
                        index=index,
                        start_time=start,
                        end_time=end,
                        text="\n".join(text_lines),
                    ))
                    index += 1
            
            i += 1
        
        return segments
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse VTT timestamp to seconds."""
        timestamp = timestamp.replace(",", ".")
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 0.0


class SRTFormatter(SubtitleFormatter):
    """SubRip (SRT) subtitle formatter."""
    
    @property
    def format_name(self) -> str:
        return "SubRip"
    
    @property
    def file_extension(self) -> str:
        return "srt"
    
    def format(self, segments: list[SubtitleSegment]) -> str:
        """Format segments to SRT format."""
        lines = []
        
        for segment in segments:
            lines.append(str(segment.index))
            start = self._format_timestamp(segment.start_time)
            end = self._format_timestamp(segment.end_time)
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        
        return "\n".join(lines)
    
    def parse(self, content: str) -> list[SubtitleSegment]:
        """Parse SRT content into segments."""
        segments = []
        blocks = re.split(r"\n\n+", content.strip())
        
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                try:
                    index = int(lines[0])
                    
                    # Parse timestamp line
                    match = re.match(
                        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
                        lines[1]
                    )
                    if match:
                        start = self._parse_timestamp(match.group(1))
                        end = self._parse_timestamp(match.group(2))
                        text = "\n".join(lines[2:])
                        
                        segments.append(SubtitleSegment(
                            index=index,
                            start_time=start,
                            end_time=end,
                            text=text,
                        ))
                except (ValueError, IndexError):
                    continue
        
        return segments
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        total_ms = int(round(seconds * 1000))
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        secs = (total_ms % 60_000) // 1000
        millis = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse SRT timestamp to seconds."""
        timestamp = timestamp.replace(",", ".")
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 0.0


class TXTFormatter(SubtitleFormatter):
    """Plain text transcript formatter."""

    @property
    def format_name(self) -> str:
        return "PlainText"

    @property
    def file_extension(self) -> str:
        return "txt"

    def format(self, segments: list[SubtitleSegment]) -> str:
        """Format segments into plain text lines."""
        return "\n".join(segment.text.strip() for segment in segments if segment.text.strip()) + "\n"

    def parse(self, content: str) -> list[SubtitleSegment]:
        """Parse plain text lines into synthetic 1-second segments."""
        segments = []
        for idx, line in enumerate(content.strip().splitlines(), 1):
            text = line.strip()
            if text:
                segments.append(
                    SubtitleSegment(
                        index=idx,
                        start_time=float(idx - 1),
                        end_time=float(idx),
                        text=text,
                    )
                )
        return segments


class LRCFormatter(SubtitleFormatter):
    """LRC lyrics subtitle formatter ([mm:ss.xx]text)."""

    @property
    def format_name(self) -> str:
        return "LRC"

    @property
    def file_extension(self) -> str:
        return "lrc"

    def format(self, segments: list[SubtitleSegment]) -> str:
        lines = []
        for segment in segments:
            total_cs = int(round(segment.start_time * 100))
            minutes = total_cs // 6000
            secs = (total_cs % 6000) // 100
            centis = total_cs % 100
            single_line = " ".join(segment.text.splitlines()).strip()
            lines.append(f"[{minutes:02d}:{secs:02d}.{centis:02d}]{single_line}")
        return "\n".join(lines) + ("\n" if lines else "")

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        pattern = re.compile(r"^\[(\d{2,}):(\d{2})[.:](\d{2,3})\](.*)$")
        raw_items: list[tuple[float, str]] = []
        for line in content.strip().splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            minutes = int(match.group(1))
            secs = int(match.group(2))
            frac_str = match.group(3)
            frac = int(frac_str) / (1000.0 if len(frac_str) == 3 else 100.0)
            start = minutes * 60 + secs + frac
            raw_items.append((start, match.group(4).strip()))

        for idx, (start, text) in enumerate(raw_items, 1):
            end = raw_items[idx][0] if idx < len(raw_items) else start + 3.0
            segments.append(
                SubtitleSegment(index=idx, start_time=start, end_time=end, text=text)
            )
        return segments


class CSVFormatter(SubtitleFormatter):
    """CSV subtitle formatter compatible with whisper-cli (`start,end,text` in ms)."""

    @property
    def format_name(self) -> str:
        return "CSV"

    @property
    def file_extension(self) -> str:
        return "csv"

    def format(self, segments: list[SubtitleSegment]) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["start", "end", "text"])
        for segment in segments:
            start_ms = int(round(segment.start_time * 1000))
            end_ms = int(round(segment.end_time * 1000))
            writer.writerow([start_ms, end_ms, segment.text])
        return buf.getvalue()

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        reader = csv.reader(io.StringIO(content.strip()))
        idx = 1
        for row in reader:
            if len(row) < 3:
                continue
            if row[0].strip().lower() == "start" and row[1].strip().lower() == "end":
                continue
            try:
                start = float(row[0].strip()) / 1000.0
                end = float(row[1].strip()) / 1000.0
                text = row[2].strip()
                segments.append(
                    SubtitleSegment(index=idx, start_time=start, end_time=end, text=text)
                )
                idx += 1
            except ValueError:
                continue
        return segments


class SubtitleFormatterFactory:
    """Factory for creating subtitle formatters."""
    
    _formatters = {
        "vtt": VTTFormatter,
        "webvtt": VTTFormatter,
        "srt": SRTFormatter,
        "subrip": SRTFormatter,
        "txt": TXTFormatter,
        "lrc": LRCFormatter,
        "csv": CSVFormatter,
    }
    
    @classmethod
    def create(cls, format_type: str) -> SubtitleFormatter:
        """
        Create a formatter for the specified format.
        
        Args:
            format_type: Format type (vtt, srt, etc.)
            
        Returns:
            Appropriate formatter instance
            
        Raises:
            ValueError: If format is not supported
        """
        format_lower = format_type.lower()
        formatter_class = cls._formatters.get(format_lower)
        
        if formatter_class is None:
            supported = list(set(cls._formatters.keys()))
            raise ValueError(
                f"Unsupported format: {format_type}. Supported: {supported}"
            )
        
        return formatter_class()
    
    @classmethod
    def get_supported_formats(cls) -> list[str]:
        """Get list of supported format names."""
        return list(set(cls._formatters.keys()))
    
    @classmethod
    def register_formatter(cls, name: str, formatter_class: type):
        """
        Register a new formatter.
        
        Args:
            name: Format name
            formatter_class: Formatter class to register
        """
        cls._formatters[name.lower()] = formatter_class


def convert_subtitle_format(
    content: str,
    source_format: str,
    target_format: str,
) -> str:
    """
    Convert subtitle content between formats.
    
    Args:
        content: Source subtitle content
        source_format: Source format (vtt, srt, etc.)
        target_format: Target format
        
    Returns:
        Converted subtitle content
    """
    source_formatter = SubtitleFormatterFactory.create(source_format)
    target_formatter = SubtitleFormatterFactory.create(target_format)
    
    segments = source_formatter.parse(content)
    return target_formatter.format(segments)


def convert_subtitle_file(
    input_path: str,
    output_path: Optional[str] = None,
    target_format: Optional[str] = None,
    source_format: Optional[str] = None,
) -> str:
    """
    Convert a subtitle file on disk from one format to another.

    Args:
        input_path: Path to the source subtitle file.
        output_path: Destination file path. If omitted, derived from
            ``input_path`` and ``target_format``.
        target_format: Target subtitle format (e.g. ``srt``, ``vtt``, ``csv``, ``lrc``, ``txt``).
            If omitted, inferred from ``output_path`` extension.
        source_format: Source subtitle format. If omitted, inferred from
            ``input_path`` extension.

    Returns:
        Path to the written converted subtitle file.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Subtitle file not found: {input_path}")

    inferred_src = os.path.splitext(input_path)[1].lstrip(".").lower()
    src_fmt = (source_format or inferred_src).lower()
    if not src_fmt:
        raise ValueError(f"Could not infer source format from '{input_path}'")

    inferred_dst = os.path.splitext(output_path)[1].lstrip(".").lower() if output_path else ""
    dst_fmt = (target_format or inferred_dst).lower()
    if not dst_fmt:
        raise ValueError("Target format must be specified via --format or output file extension")

    target_formatter = SubtitleFormatterFactory.create(dst_fmt)
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.{target_formatter.file_extension}"

    with open(input_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    converted = convert_subtitle_format(raw_content, src_fmt, dst_fmt)

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(converted)

    return output_path
