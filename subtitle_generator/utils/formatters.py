"""
Subtitle format converters with Factory pattern.

Provides formatters for different subtitle formats (VTT, SRT, etc.)
with a factory for creating the appropriate formatter.
"""

import logging
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
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse SRT timestamp to seconds."""
        timestamp = timestamp.replace(",", ".")
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 0.0


class SubtitleFormatterFactory:
    """Factory for creating subtitle formatters."""
    
    _formatters = {
        "vtt": VTTFormatter,
        "webvtt": VTTFormatter,
        "srt": SRTFormatter,
        "subrip": SRTFormatter,
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
