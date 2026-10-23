"""
Unit tests for subtitle formatters.
"""

import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from subtitle_generator.utils.formatters import (
    SubtitleSegment,
    VTTFormatter,
    SRTFormatter,
    TXTFormatter,
    LRCFormatter,
    CSVFormatter,
    SubtitleFormatterFactory,
    convert_subtitle_format,
    convert_subtitle_file,
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

    def test_vtt_to_csv_lrc_txt_and_roundtrip(self, tmp_path):
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.250
First caption

00:00:04.000 --> 00:00:06.500
Second caption
"""
        csv_content = convert_subtitle_format(vtt_content, "vtt", "csv")
        assert "start,end,text" in csv_content
        assert "1000,3250,First caption" in csv_content

        srt_from_csv = convert_subtitle_format(csv_content, "csv", "srt")
        assert "00:00:01,000 --> 00:00:03,250" in srt_from_csv
        assert "Second caption" in srt_from_csv

        lrc_content = convert_subtitle_format(vtt_content, "vtt", "lrc")
        assert "[00:01.00]First caption" in lrc_content
        assert "[00:04.00]Second caption" in lrc_content

        txt_content = convert_subtitle_format(vtt_content, "vtt", "txt")
        assert txt_content.strip() == "First caption\nSecond caption"

        src_file = tmp_path / "sample.vtt"
        src_file.write_text(vtt_content, encoding="utf-8")
        out_path = convert_subtitle_file(str(src_file), target_format="srt")
        assert out_path.endswith("sample.srt")
        assert os.path.isfile(out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            assert "00:00:01,000 --> 00:00:03,250" in f.read()
