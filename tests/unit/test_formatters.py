"""
Unit tests for subtitle formatters.
"""

import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.formatters import (
    SubtitleSegment,
    VTTFormatter,
    SRTFormatter,
    SubtitleFormatterFactory,
    convert_subtitle_format,
)


class TestSubtitleSegment:
    """Tests for SubtitleSegment dataclass."""
    
    def test_segment_creation(self):
        """Test creating a subtitle segment."""
        segment = SubtitleSegment(
            index=1,
            start_time=0.0,
            end_time=5.0,
            text="Hello, world!",
        )
        
        assert segment.index == 1
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.text == "Hello, world!"
    
    def test_segment_duration(self):
        """Test segment duration calculation."""
        segment = SubtitleSegment(
            index=1,
            start_time=10.5,
            end_time=15.75,
            text="Test",
        )
        
        assert segment.duration == 5.25


class TestVTTFormatter:
    """Tests for VTT formatter."""
    
    def test_format_segments(self):
        """Test formatting segments to VTT."""
        formatter = VTTFormatter()
        segments = [
            SubtitleSegment(1, 0.0, 3.5, "First line"),
            SubtitleSegment(2, 4.0, 7.0, "Second line"),
        ]
        
        result = formatter.format(segments)
        
        assert "WEBVTT" in result
        assert "00:00:00.000 --> 00:00:03.500" in result
        assert "First line" in result
        assert "Second line" in result
    
    def test_parse_vtt(self):
        """Test parsing VTT content."""
        formatter = VTTFormatter()
        content = """WEBVTT

00:00:00.000 --> 00:00:03.500
First line

00:00:04.000 --> 00:00:07.000
Second line
"""
        
        segments = formatter.parse(content)
        
        assert len(segments) == 2
        assert segments[0].text == "First line"
        assert segments[1].start_time == 4.0


class TestSRTFormatter:
    """Tests for SRT formatter."""
    
    def test_format_segments(self):
        """Test formatting segments to SRT."""
        formatter = SRTFormatter()
        segments = [
            SubtitleSegment(1, 0.0, 3.5, "First line"),
            SubtitleSegment(2, 4.0, 7.0, "Second line"),
        ]
        
        result = formatter.format(segments)
        
        assert "1\n" in result
        assert "00:00:00,000 --> 00:00:03,500" in result
        assert "First line" in result
    
    def test_parse_srt(self):
        """Test parsing SRT content."""
        formatter = SRTFormatter()
        content = """1
00:00:00,000 --> 00:00:03,500
First line

2
00:00:04,000 --> 00:00:07,000
Second line
"""
        
        segments = formatter.parse(content)
        
        assert len(segments) == 2
        assert segments[0].index == 1
        assert segments[1].text == "Second line"


class TestSubtitleFormatterFactory:
    """Tests for formatter factory."""
    
    def test_create_vtt_formatter(self):
        """Test creating VTT formatter."""
        formatter = SubtitleFormatterFactory.create("vtt")
        assert isinstance(formatter, VTTFormatter)
    
    def test_create_srt_formatter(self):
        """Test creating SRT formatter."""
        formatter = SubtitleFormatterFactory.create("srt")
        assert isinstance(formatter, SRTFormatter)
    
    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            SubtitleFormatterFactory.create("invalid")


class TestFormatConversion:
    """Tests for format conversion."""
    
    def test_vtt_to_srt_conversion(self):
        """Test converting VTT to SRT."""
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:03.500
Hello, world!
"""
        
        srt_content = convert_subtitle_format(vtt_content, "vtt", "srt")
        
        assert "1\n" in srt_content
        assert "00:00:00,000 --> 00:00:03,500" in srt_content
        assert "Hello, world!" in srt_content
