"""Industry-standard subtitle post-processing, reflow, QC linting, and timing shift.

Implements Netflix, BBC, and Reels/Shorts broadcast readability rules:
- Characters Per Line (CPL) & Max Lines
- Reading speed (Characters Per Second / CPS)
- Min/Max cue duration & minimum inter-cue gap
- Natural linguistic line breaking
- Whisper silence hallucination / repetition scrubbing
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .formatters import SubtitleFormatterFactory, SubtitleSegment

_NON_BREAKING_TAILS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "by", "with", "from", "and", "or", "but",
}

_HALLUCINATION_EXACT = {
    "[blank_audio]",
    "(blank audio)",
    "[music]",
    "[silence]",
    "...",
}


@dataclass(frozen=True)
class SubtitlePreset:
    name: str
    max_cpl: int
    max_lines: int
    max_cps: float
    min_duration: float
    max_duration: float
    min_gap: float = 0.083  # ~2 frames at 24fps


PRESETS: dict[str, SubtitlePreset] = {
    "netflix": SubtitlePreset(
        name="netflix",
        max_cpl=42,
        max_lines=2,
        max_cps=20.0,
        min_duration=0.833,
        max_duration=7.0,
        min_gap=0.083,
    ),
    "netflix-kids": SubtitlePreset(
        name="netflix-kids",
        max_cpl=42,
        max_lines=2,
        max_cps=17.0,
        min_duration=0.833,
        max_duration=7.0,
        min_gap=0.083,
    ),
    "bbc": SubtitlePreset(
        name="bbc",
        max_cpl=37,
        max_lines=2,
        max_cps=17.0,
        min_duration=1.0,
        max_duration=6.0,
        min_gap=0.083,
    ),
    "reels": SubtitlePreset(
        name="reels",
        max_cpl=18,
        max_lines=1,
        max_cps=24.0,
        min_duration=0.3,
        max_duration=2.5,
        min_gap=0.02,
    ),
    "shorts": SubtitlePreset(
        name="shorts",
        max_cpl=18,
        max_lines=1,
        max_cps=24.0,
        min_duration=0.3,
        max_duration=2.5,
        min_gap=0.02,
    ),
}


def get_preset(name: str) -> SubtitlePreset:
    key = name.strip().lower()
    if key not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {', '.join(sorted(PRESETS))}")
    return PRESETS[key]


def scrub_hallucinations(segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
    """Remove empty cues, [BLANK_AUDIO] markers, and Whisper repetition loops."""
    cleaned: list[SubtitleSegment] = []
    repeat_run = 0
    prev_norm = ""

    for seg in segments:
        text = " ".join(seg.text.split()).strip()
        if not text:
            continue
        norm = re.sub(r"[^\w\s]", "", text.lower()).strip()
        if text.lower() in _HALLUCINATION_EXACT or not norm:
            continue

        if norm == prev_norm:
            repeat_run += 1
            # Drop 3rd+ consecutive identical cue (classic Whisper silence loop)
            if repeat_run >= 2:
                continue
        else:
            repeat_run = 0
            prev_norm = norm

        cleaned.append(
            SubtitleSegment(
                index=len(cleaned) + 1,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text.strip(),
                words=list(seg.words),
                speaker=seg.speaker,
            )
        )
    return cleaned


def wrap_lines_balanced(text: str, max_cpl: int = 42, max_lines: int = 2) -> str:
    """Wrap text into balanced lines respecting CPL and natural linguistic breaks."""
    flat = " ".join(text.split()).strip()
    if not flat:
        return ""
    if len(flat) <= max_cpl or max_lines <= 1:
        return flat

    words = flat.split(" ")
    if len(words) <= 1:
        return flat

    if max_lines == 2:
        best_split: Optional[tuple[str, str]] = None
        best_score = float("inf")
        for i in range(1, len(words)):
            line1 = " ".join(words[:i])
            line2 = " ".join(words[i:])
            if len(line1) > max_cpl or len(line2) > max_cpl:
                continue
            # Prefer slightly bottom-heavy balanced lines + breaks after punctuation
            balance = abs(len(line1) - len(line2))
            if len(line1) > len(line2):
                balance += 2
            last_w = words[i - 1]
            if last_w[-1] in ",.;:!?—-":
                balance -= 8
            if last_w.lower().strip(",.;:!?") in _NON_BREAKING_TAILS:
                balance += 10
            if balance < best_score:
                best_score = balance
                best_split = (line1, line2)
        if best_split:
            return f"{best_split[0]}\n{best_split[1]}"

    # Greedy fallback for multi-line or oversized tokens — never drop trailing text
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip() if current else w
        if len(candidate) <= max_cpl or not current:
            current = candidate
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        merged_tail = " ".join(lines[max_lines - 1 :])
        lines = lines[: max_lines - 1] + [merged_tail]
    return "\n".join(lines)


def _split_long_segment(seg: SubtitleSegment, preset: SubtitlePreset) -> list[SubtitleSegment]:
    """Split a segment that exceeds max_cpl * max_lines, line wrapping, or max_duration."""
    flat = " ".join(seg.text.split()).strip()
    wrapped = wrap_lines_balanced(flat, preset.max_cpl, preset.max_lines)
    wrapped_lines = wrapped.splitlines()
    fits_lines = len(wrapped_lines) <= preset.max_lines and all(
        len(line) <= preset.max_cpl for line in wrapped_lines
    )
    if fits_lines and seg.duration <= preset.max_duration:
        return [
            SubtitleSegment(
                index=seg.index,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=wrapped,
                words=list(seg.words),
                speaker=seg.speaker,
            )
        ]

    # Split into chunks that each fit cleanly within max_cpl * max_lines
    words = flat.split(" ")
    max_block_chars = max(preset.max_cpl, int(preset.max_cpl * preset.max_lines * 0.9))
    chunks: list[list[str]] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add_len = len(w) + (1 if cur else 0)
        if cur and (cur_len + add_len > max_block_chars):
            chunks.append(cur)
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += add_len
    if cur:
        chunks.append(cur)

    use_words = bool(seg.words) and len(seg.words) == len(words)
    total_chars = sum(max(1, len(" ".join(c))) for c in chunks)
    total_dur = max(0.01, seg.end_time - seg.start_time)
    out: list[SubtitleSegment] = []
    cursor = seg.start_time
    word_idx = 0

    for chunk in chunks:
        chunk_text = " ".join(chunk)
        chunk_words = seg.words[word_idx : word_idx + len(chunk)] if use_words else []
        word_idx += len(chunk)

        if chunk_words:
            c_start = chunk_words[0].start_time
            c_end = chunk_words[-1].end_time
        else:
            share = len(chunk_text) / total_chars
            c_start = cursor
            c_end = min(seg.end_time, cursor + total_dur * share)
            cursor = c_end

        out.append(
            SubtitleSegment(
                index=0,
                start_time=c_start,
                end_time=max(c_end, c_start + 0.1),
                text=wrap_lines_balanced(chunk_text, preset.max_cpl, preset.max_lines),
                words=chunk_words,
                speaker=seg.speaker,
            )
        )
    return out


def reflow_segments(
    segments: list[SubtitleSegment],
    preset_name: str = "netflix",
    scrub: bool = True,
) -> list[SubtitleSegment]:
    """Reflow subtitle segments to comply with a broadcast/creator preset."""
    preset = get_preset(preset_name)
    working = scrub_hallucinations(segments) if scrub else list(segments)
    working.sort(key=lambda s: (s.start_time, s.end_time))

    expanded: list[SubtitleSegment] = []
    for seg in working:
        expanded.extend(_split_long_segment(seg, preset))
    expanded.sort(key=lambda s: (s.start_time, s.end_time))

    # Enforce min_duration, max_duration, and non-overlapping min_gap
    for i, seg in enumerate(expanded):
        if seg.duration < preset.min_duration:
            seg.end_time = seg.start_time + preset.min_duration
        if seg.duration > preset.max_duration:
            seg.end_time = seg.start_time + preset.max_duration

        if i + 1 < len(expanded):
            next_seg = expanded[i + 1]
            max_allowed_end = next_seg.start_time - preset.min_gap
            if seg.end_time > max_allowed_end:
                if max_allowed_end > seg.start_time:
                    seg.end_time = max_allowed_end
                else:
                    seg.end_time = max(seg.start_time, next_seg.start_time)

        seg.index = i + 1

    return expanded


def shift_segments(segments: list[SubtitleSegment], offset_ms: int) -> list[SubtitleSegment]:
    """Shift all segment (and word) timestamps by ``offset_ms`` milliseconds."""
    delta = offset_ms / 1000.0
    shifted: list[SubtitleSegment] = []
    for idx, seg in enumerate(segments, 1):
        new_start = max(0.0, seg.start_time + delta)
        new_end = max(new_start + 0.05, seg.end_time + delta)
        new_words = [
            type(w)(
                word=w.word,
                start_time=max(0.0, w.start_time + delta),
                end_time=max(0.0, w.end_time + delta),
                probability=w.probability,
            )
            for w in seg.words
        ]
        shifted.append(
            SubtitleSegment(
                index=idx,
                start_time=new_start,
                end_time=new_end,
                text=seg.text,
                words=new_words,
                speaker=seg.speaker,
            )
        )
    return shifted


def shift_subtitle_file(
    input_path: str,
    offset_ms: int,
    output_path: Optional[str] = None,
) -> str:
    """Shift timestamps in a subtitle file on disk and write the result."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Subtitle file not found: {input_path}")
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    formatter = SubtitleFormatterFactory.create(ext)
    with open(input_path, "r", encoding="utf-8") as f:
        segments = formatter.parse(f.read())
    shifted = shift_segments(segments, offset_ms)
    dest = output_path or input_path
    out_dir = os.path.dirname(os.path.abspath(dest))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(formatter.format(shifted))
    return dest


@dataclass
class LintIssue:
    cue_index: int
    code: str
    severity: str  # "error" or "warning"
    message: str


@dataclass
class LintReport:
    standard: str
    total_cues: int
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "standard": self.standard,
            "total_cues": self.total_cues,
            "passed": self.passed,
            "issue_count": len(self.issues),
            "issues": [
                {
                    "cue_index": i.cue_index,
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                }
                for i in self.issues
            ],
        }


def lint_segments(segments: list[SubtitleSegment], standard: str = "netflix") -> LintReport:
    """Validate subtitle segments against an industry standard (netflix/bbc/reels)."""
    preset = get_preset(standard)
    issues: list[LintIssue] = []

    for i, seg in enumerate(segments):
        cue_id = seg.index or (i + 1)
        lines = seg.text.splitlines()
        if not seg.text.strip():
            issues.append(LintIssue(cue_id, "EMPTY_TEXT", "error", "Cue has empty text"))
            continue

        if len(lines) > preset.max_lines:
            issues.append(
                LintIssue(
                    cue_id,
                    "MAX_LINES",
                    "error",
                    f"{len(lines)} lines exceeds max {preset.max_lines}",
                )
            )

        for line in lines:
            if len(line) > preset.max_cpl:
                issues.append(
                    LintIssue(
                        cue_id,
                        "MAX_CPL",
                        "error",
                        f"Line length {len(line)} exceeds max {preset.max_cpl} CPL: {line!r}",
                    )
                )

        dur = seg.duration
        if dur < preset.min_duration - 1e-6:
            issues.append(
                LintIssue(
                    cue_id,
                    "MIN_DURATION",
                    "warning",
                    f"Duration {dur:.2f}s is below minimum {preset.min_duration:.2f}s",
                )
            )
        if dur > preset.max_duration + 1e-6:
            issues.append(
                LintIssue(
                    cue_id,
                    "MAX_DURATION",
                    "warning",
                    f"Duration {dur:.2f}s exceeds maximum {preset.max_duration:.2f}s",
                )
            )

        char_count = len("".join(lines))
        if dur > 0:
            cps = char_count / dur
            if cps > preset.max_cps + 0.1:
                issues.append(
                    LintIssue(
                        cue_id,
                        "MAX_CPS",
                        "warning",
                        f"Reading speed {cps:.1f} CPS exceeds max {preset.max_cps:.1f} CPS",
                    )
                )

        if i + 1 < len(segments):
            nxt = segments[i + 1]
            if seg.end_time > nxt.start_time + 1e-6:
                issues.append(
                    LintIssue(
                        cue_id,
                        "OVERLAP",
                        "error",
                        f"Cue overlaps next cue ({seg.end_time:.3f}s > {nxt.start_time:.3f}s)",
                    )
                )

    return LintReport(standard=preset.name, total_cues=len(segments), issues=issues)


def lint_subtitle_file(input_path: str, standard: str = "netflix") -> LintReport:
    """Parse and lint a subtitle file on disk."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Subtitle file not found: {input_path}")
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    formatter = SubtitleFormatterFactory.create(ext)
    with open(input_path, "r", encoding="utf-8") as f:
        segments = formatter.parse(f.read())
    return lint_segments(segments, standard=standard)
