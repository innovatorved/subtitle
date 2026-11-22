"""Subtitle format converters with Factory pattern.

Supports VTT, SRT, ASS (with styled & karaoke presets), TTML, JSON
(including whisper.cpp `-oj` / `-ojf` word timings), CSV, LRC, and TXT.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class WordTiming:
    """Represents a single word with precise start/end timestamps."""

    word: str
    start_time: float  # seconds
    end_time: float  # seconds
    probability: float = 1.0


@dataclass
class SubtitleSegment:
    """Represents a single subtitle segment."""

    index: int
    start_time: float  # seconds
    end_time: float  # seconds
    text: str
    words: list[WordTiming] = field(default_factory=list)
    speaker: Optional[str] = None

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return max(0.0, self.end_time - self.start_time)


class SubtitleFormatter(ABC):
    """Abstract base class for subtitle formatters."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def format(self, segments: list[SubtitleSegment]) -> str:
        pass

    @abstractmethod
    def parse(self, content: str) -> list[SubtitleSegment]:
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
        lines = ["WEBVTT", ""]
        for segment in segments:
            start = self._format_timestamp(segment.start_time)
            end = self._format_timestamp(segment.end_time)
            lines.append(f"{start} --> {end}")
            text = f"<v {segment.speaker}>{segment.text}" if segment.speaker else segment.text
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        normalized = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.strip().split("\n")

        i = 0
        while i < len(lines) and "-->" not in lines[i]:
            i += 1

        index = 1
        while i < len(lines):
            line = lines[i].strip()
            if "-->" in line:
                match = re.match(
                    r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})",
                    line,
                )
                if match:
                    start = self._parse_timestamp(match.group(1))
                    end = self._parse_timestamp(match.group(2))

                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1

                    segments.append(
                        SubtitleSegment(
                            index=index,
                            start_time=start,
                            end_time=end,
                            text="\n".join(text_lines),
                        )
                    )
                    index += 1
            i += 1
        return segments

    def _format_timestamp(self, seconds: float) -> str:
        total_ms = int(round(max(0.0, seconds) * 1000))
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        secs = (total_ms % 60_000) // 1000
        millis = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _parse_timestamp(self, timestamp: str) -> float:
        timestamp = timestamp.replace(",", ".")
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
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
        lines = []
        for idx, segment in enumerate(segments, 1):
            lines.append(str(segment.index or idx))
            start = self._format_timestamp(segment.start_time)
            end = self._format_timestamp(segment.end_time)
            lines.append(f"{start} --> {end}")
            text = f"[{segment.speaker}] {segment.text}" if segment.speaker else segment.text
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        normalized = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        blocks = re.split(r"\n\n+", normalized.strip())

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                try:
                    index = int(lines[0])
                    match = re.match(
                        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})",
                        lines[1],
                    )
                    if match:
                        start = self._parse_timestamp(match.group(1))
                        end = self._parse_timestamp(match.group(2))
                        text = "\n".join(lines[2:])
                        segments.append(
                            SubtitleSegment(
                                index=index,
                                start_time=start,
                                end_time=end,
                                text=text,
                            )
                        )
                except (ValueError, IndexError):
                    continue
        return segments

    def _format_timestamp(self, seconds: float) -> str:
        total_ms = int(round(max(0.0, seconds) * 1000))
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        secs = (total_ms % 60_000) // 1000
        millis = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _parse_timestamp(self, timestamp: str) -> float:
        timestamp = timestamp.replace(",", ".")
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        return 0.0


class ASSFormatter(SubtitleFormatter):
    """Advanced SubStation Alpha (ASS) formatter with broadcast & creator styles.

    Styles:
      - ``clean``: Crisp white sans-serif with black outline & subtle drop shadow.
      - ``box``: Semi-transparent dark rounded box behind text (YouTube/Netflix look).
      - ``karaoke``: Bold high-contrast yellow highlight word-by-word (TikTok/Reels/Shorts).
      - ``cinema``: Subtle warm off-white serif-friendly lower-third styling.
    """

    STYLE_PRESETS: dict[str, dict[str, Any]] = {
        "clean": {
            "font": "Arial",
            "font_size": 52,
            "primary": "&H00FFFFFF",
            "secondary": "&H0000FFFF",
            "outline_color": "&H00000000",
            "back_color": "&H80000000",
            "bold": 0,
            "border_style": 1,
            "outline": 3,
            "shadow": 1,
            "margin_v": 45,
        },
        "box": {
            "font": "Arial",
            "font_size": 48,
            "primary": "&H00FFFFFF",
            "secondary": "&H0000FFFF",
            "outline_color": "&HB4000000",
            "back_color": "&HB4000000",
            "bold": 0,
            "border_style": 3,
            "outline": 10,
            "shadow": 0,
            "margin_v": 50,
        },
        "karaoke": {
            "font": "Arial Black",
            "font_size": 68,
            "primary": "&H0000FFFF",  # Highlighted yellow (ASS BGR)
            "secondary": "&H00FFFFFF",  # Unspoken white
            "outline_color": "&H00000000",
            "back_color": "&H90000000",
            "bold": -1,
            "border_style": 1,
            "outline": 5,
            "shadow": 2,
            "margin_v": 120,
        },
        "cinema": {
            "font": "Georgia",
            "font_size": 46,
            "primary": "&H00F2F2F2",
            "secondary": "&H0000D7FF",
            "outline_color": "&H00101010",
            "back_color": "&H70000000",
            "bold": 0,
            "border_style": 1,
            "outline": 2,
            "shadow": 2,
            "margin_v": 40,
        },
    }

    _POSITION_ALIGNMENT = {
        "bottom": 2,
        "center": 5,
        "top": 8,
    }

    def __init__(
        self,
        style: str = "clean",
        font: Optional[str] = None,
        font_size: Optional[int] = None,
        position: str = "bottom",
        play_res_x: int = 1920,
        play_res_y: int = 1080,
    ):
        self.style_name = style if style in self.STYLE_PRESETS else "clean"
        self.font = font
        self.font_size = font_size
        self.position = position if position in self._POSITION_ALIGNMENT else "bottom"
        self.play_res_x = play_res_x
        self.play_res_y = play_res_y

    @property
    def format_name(self) -> str:
        return "ASS"

    @property
    def file_extension(self) -> str:
        return "ass"

    def _format_timestamp(self, seconds: float) -> str:
        total_cs = int(round(max(0.0, seconds) * 100))
        hours = total_cs // 360_000
        minutes = (total_cs % 360_000) // 6000
        secs = (total_cs % 6000) // 100
        centis = total_cs % 100
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def _parse_timestamp(self, ts: str) -> float:
        parts = ts.strip().split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return 0.0

    def _render_karaoke_text(self, segment: SubtitleSegment) -> str:
        """Render word-by-word ``{\\kf<cs>}`` karaoke tags when word timings exist."""
        if segment.words:
            pieces: list[str] = []
            for w in segment.words:
                dur_cs = max(1, int(round((w.end_time - w.start_time) * 100)))
                word_txt = w.word.replace("\n", "\\N")
                pieces.append(f"{{\\kf{dur_cs}}}{word_txt}")
            return " ".join(pieces)

        # Fallback: distribute cue duration proportionally across words
        words = segment.text.replace("\n", " ").split()
        if not words:
            return ""
        total_cs = max(len(words), int(round(segment.duration * 100)))
        total_chars = sum(max(1, len(w)) for w in words)
        pieces = []
        for w in words:
            dur_cs = max(1, int(round(total_cs * max(1, len(w)) / total_chars)))
            pieces.append(f"{{\\kf{dur_cs}}}{w}")
        return " ".join(pieces)

    def format(self, segments: list[SubtitleSegment]) -> str:
        cfg = dict(self.STYLE_PRESETS[self.style_name])
        font = self.font or cfg["font"]
        font_size = self.font_size or cfg["font_size"]
        alignment = self._POSITION_ALIGNMENT[self.position]

        header = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.play_res_x}",
            f"PlayResY: {self.play_res_y}",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding",
            (
                f"Style: Default,{font},{font_size},{cfg['primary']},{cfg['secondary']},"
                f"{cfg['outline_color']},{cfg['back_color']},{cfg['bold']},0,0,0,"
                f"100,100,0,0,{cfg['border_style']},{cfg['outline']},{cfg['shadow']},"
                f"{alignment},40,40,{cfg['margin_v']},1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        lines = list(header)
        for seg in segments:
            start = self._format_timestamp(seg.start_time)
            end = self._format_timestamp(seg.end_time)
            speaker = seg.speaker or ""
            if self.style_name == "karaoke":
                text = self._render_karaoke_text(seg)
            else:
                text = seg.text.replace("\n", "\\N")
                if speaker:
                    text = f"{speaker}: {text}"
            lines.append(f"Dialogue: 0,{start},{end},Default,{speaker},0,0,0,,{text}")
        return "\n".join(lines) + "\n"

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments: list[SubtitleSegment] = []
        idx = 1
        for raw_line in content.lstrip("\ufeff").splitlines():
            line = raw_line.strip()
            if not line.startswith("Dialogue:"):
                continue
            payload = line[len("Dialogue:") :].strip()
            parts = payload.split(",", 9)
            if len(parts) < 10:
                continue
            start = self._parse_timestamp(parts[1])
            end = self._parse_timestamp(parts[2])
            speaker = parts[4].strip() or None
            raw_text = parts[9]
            # Strip ASS override tags like {\kf25}
            clean_text = re.sub(r"\{[^}]*\}", "", raw_text).replace("\\N", "\n").replace("\\n", "\n").strip()
            segments.append(
                SubtitleSegment(
                    index=idx,
                    start_time=start,
                    end_time=end,
                    text=clean_text,
                    speaker=speaker,
                )
            )
            idx += 1
        return segments


class TTMLFormatter(SubtitleFormatter):
    """W3C TTML (Timed Text Markup Language) broadcast subtitle formatter."""

    @property
    def format_name(self) -> str:
        return "TTML"

    @property
    def file_extension(self) -> str:
        return "ttml"

    def _format_timestamp(self, seconds: float) -> str:
        total_ms = int(round(max(0.0, seconds) * 1000))
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        secs = (total_ms % 60_000) // 1000
        millis = total_ms % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _parse_timestamp(self, ts: str) -> float:
        ts = ts.strip()
        if ts.endswith("s"):
            try:
                return float(ts[:-1])
            except ValueError:
                return 0.0
        parts = ts.replace(",", ".").split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return 0.0

    def format(self, segments: list[SubtitleSegment]) -> str:
        def _esc(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<tt xml:lang="en" xmlns="http://www.w3.org/ns/ttml">',
            "  <body>",
            "    <div>",
        ]
        for seg in segments:
            begin = self._format_timestamp(seg.start_time)
            end = self._format_timestamp(seg.end_time)
            body = "<br/>".join(_esc(part) for part in seg.text.splitlines())
            lines.append(f'      <p begin="{begin}" end="{end}">{body}</p>')
        lines.extend(["    </div>", "  </body>", "</tt>", ""])
        return "\n".join(lines)

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments: list[SubtitleSegment] = []
        root = ET.fromstring(content.lstrip("\ufeff").strip())
        idx = 1
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag != "p":
                continue
            begin = elem.attrib.get("begin", "00:00:00.000")
            end = elem.attrib.get("end", "00:00:00.000")
            # Preserve <br/> as newlines
            parts: list[str] = []
            if elem.text:
                parts.append(elem.text)
            for child in elem:
                child_tag = child.tag.split("}")[-1]
                if child_tag == "br":
                    parts.append("\n")
                elif child.text:
                    parts.append(child.text)
                if child.tail:
                    parts.append(child.tail)
            text = "".join(parts).strip()
            segments.append(
                SubtitleSegment(
                    index=idx,
                    start_time=self._parse_timestamp(begin),
                    end_time=self._parse_timestamp(end),
                    text=text,
                )
            )
            idx += 1
        return segments


class JSONFormatter(SubtitleFormatter):
    """Structured JSON subtitle formatter (compatible with whisper.cpp `-oj` / `-ojf`)."""

    @property
    def format_name(self) -> str:
        return "JSON"

    @property
    def file_extension(self) -> str:
        return "json"

    def format(self, segments: list[SubtitleSegment]) -> str:
        payload = {
            "segments": [
                {
                    "index": seg.index,
                    "start": round(seg.start_time, 3),
                    "end": round(seg.end_time, 3),
                    "text": seg.text,
                    **({"speaker": seg.speaker} if seg.speaker else {}),
                    **(
                        {
                            "words": [
                                {
                                    "word": w.word,
                                    "start": round(w.start_time, 3),
                                    "end": round(w.end_time, 3),
                                    "probability": round(w.probability, 4),
                                }
                                for w in seg.words
                            ]
                        }
                        if seg.words
                        else {}
                    ),
                }
                for seg in segments
            ]
        }
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    def parse(self, content: str) -> list[SubtitleSegment]:
        data = json.loads(content.lstrip("\ufeff"))
        segments: list[SubtitleSegment] = []

        # Format 1: whisper.cpp `-oj` / `-ojf` output (`transcription` list)
        if isinstance(data, dict) and "transcription" in data:
            current_speaker_id = 1
            has_tdrz = any(bool(item.get("speaker_turn_next")) for item in data["transcription"])
            for idx, item in enumerate(data["transcription"], 1):
                offsets = item.get("offsets") or {}
                start = float(offsets.get("from", 0)) / 1000.0
                end = float(offsets.get("to", 0)) / 1000.0
                text = (item.get("text") or "").strip()

                # Merge BPE subword tokens into full whitespace-delimited words
                words: list[WordTiming] = []
                for tok in item.get("tokens") or []:
                    raw_tok = tok.get("text") or ""
                    stripped = raw_tok.strip()
                    if not stripped or (stripped.startswith("[") and stripped.endswith("]")):
                        continue
                    tok_off = tok.get("offsets") or {}
                    w_start = float(tok_off.get("from", offsets.get("from", 0))) / 1000.0
                    w_end = float(tok_off.get("to", offsets.get("to", 0))) / 1000.0
                    prob = float(tok.get("p", 1.0))
                    starts_new_word = (not words) or raw_tok[:1].isspace()
                    if starts_new_word:
                        words.append(
                            WordTiming(word=stripped, start_time=w_start, end_time=w_end, probability=prob)
                        )
                    else:
                        prev = words[-1]
                        prev.word += stripped
                        prev.end_time = max(prev.end_time, w_end)
                        prev.probability = min(prev.probability, prob)

                speaker = f"Speaker {current_speaker_id}" if has_tdrz else None
                if item.get("speaker_turn_next"):
                    current_speaker_id = 2 if current_speaker_id == 1 else 1
                segments.append(
                    SubtitleSegment(
                        index=idx,
                        start_time=start,
                        end_time=end,
                        text=text,
                        words=words,
                        speaker=speaker,
                    )
                )
            return segments

        # Format 2: subtitle-generator JSON (`segments` list)
        items = data.get("segments", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for idx, item in enumerate(items, 1):
            words = [
                WordTiming(
                    word=w["word"],
                    start_time=float(w["start"]),
                    end_time=float(w["end"]),
                    probability=float(w.get("probability", 1.0)),
                )
                for w in item.get("words", [])
            ]
            segments.append(
                SubtitleSegment(
                    index=int(item.get("index", idx)),
                    start_time=float(item.get("start", 0.0)),
                    end_time=float(item.get("end", 0.0)),
                    text=str(item.get("text", "")),
                    words=words,
                    speaker=item.get("speaker"),
                )
            )
        return segments


class TXTFormatter(SubtitleFormatter):
    """Plain text transcript formatter."""

    @property
    def format_name(self) -> str:
        return "PlainText"

    @property
    def file_extension(self) -> str:
        return "txt"

    def format(self, segments: list[SubtitleSegment]) -> str:
        lines = [segment.text.strip() for segment in segments if segment.text.strip()]
        return "\n".join(lines) + ("\n" if lines else "")

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        for idx, line in enumerate(content.lstrip("\ufeff").strip().splitlines(), 1):
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
            total_cs = int(round(max(0.0, segment.start_time) * 100))
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
        for line in content.lstrip("\ufeff").strip().splitlines():
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
            start_ms = int(round(max(0.0, segment.start_time) * 1000))
            end_ms = int(round(max(0.0, segment.end_time) * 1000))
            writer.writerow([start_ms, end_ms, segment.text])
        return buf.getvalue()

    def parse(self, content: str) -> list[SubtitleSegment]:
        segments = []
        reader = csv.reader(io.StringIO(content.lstrip("\ufeff").strip()))
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

    _formatters: dict[str, type[SubtitleFormatter]] = {
        "vtt": VTTFormatter,
        "webvtt": VTTFormatter,
        "srt": SRTFormatter,
        "subrip": SRTFormatter,
        "ass": ASSFormatter,
        "ssa": ASSFormatter,
        "ttml": TTMLFormatter,
        "json": JSONFormatter,
        "txt": TXTFormatter,
        "lrc": LRCFormatter,
        "csv": CSVFormatter,
    }

    @classmethod
    def create(cls, format_type: str, **kwargs: Any) -> SubtitleFormatter:
        format_lower = format_type.lower()
        formatter_class = cls._formatters.get(format_lower)
        if formatter_class is None:
            supported = sorted(set(cls._formatters.keys()))
            raise ValueError(
                f"Unsupported format: {format_type}. Supported: {supported}"
            )
        if kwargs and formatter_class is ASSFormatter:
            return ASSFormatter(**kwargs)
        return formatter_class()

    @classmethod
    def get_supported_formats(cls) -> list[str]:
        return list(set(cls._formatters.keys()))

    @classmethod
    def register_formatter(cls, name: str, formatter_class: type[SubtitleFormatter]) -> None:
        cls._formatters[name.lower()] = formatter_class


def convert_subtitle_format(
    content: str,
    source_format: str,
    target_format: str,
    **target_kwargs: Any,
) -> str:
    """Convert subtitle content between formats."""
    source_formatter = SubtitleFormatterFactory.create(source_format)
    target_formatter = SubtitleFormatterFactory.create(target_format, **target_kwargs)
    segments = source_formatter.parse(content)
    return target_formatter.format(segments)


def convert_subtitle_file(
    input_path: str,
    output_path: Optional[str] = None,
    target_format: Optional[str] = None,
    source_format: Optional[str] = None,
    **target_kwargs: Any,
) -> str:
    """Convert a subtitle file on disk from one format to another."""
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

    target_formatter = SubtitleFormatterFactory.create(dst_fmt, **target_kwargs)
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.{target_formatter.file_extension}"

    with open(input_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    converted = convert_subtitle_format(raw_content, src_fmt, dst_fmt, **target_kwargs)

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(converted)

    return output_path
