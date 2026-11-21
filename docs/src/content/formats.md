---
title: Formats & Embedding
description: Supported subtitle output formats, offline format conversion, soft muxing (--merge), and hard burning (--burn).
---

## Supported Subtitle Formats

| Format | Flag | Description | Convertible via `subtitle convert` |
|--------|------|-------------|-------------------------------------|
| **WebVTT** | `--format vtt` | Web video standard (`HH:MM:SS.mmm`) *(default)* | Yes |
| **SubRip** | `--format srt` | Universal desktop & editor format (`HH:MM:SS,mmm`) | Yes |
| **Plain Text** | `--format txt` | Clean transcript without timestamps | Yes |
| **LRC** | `--format lrc` | Synchronized lyrics format (`[mm:ss.xx]`) | Yes |
| **CSV** | `--format csv` | Millisecond-aligned `start,end,text` spreadsheet | Yes |
| **JSON** | `--format json` | Structured `whisper.cpp` JSON output | Generation only |

---

## Converting Subtitle Files

Convert any existing subtitle file without re-running transcription:

```bash
# Infer formats from file extensions
subtitle convert video.vtt video.srt

# Derive output filename automatically from --format
subtitle convert video.vtt --format srt
subtitle convert video.srt --format txt
subtitle convert video.srt --format csv

# Specify source format explicitly
subtitle convert captions.raw captions.vtt --source-format srt
```

<Aside type="note">
Parsers automatically normalize Windows (`\r\n`) and Unix (`\n`) line endings, strip UTF-8 BOM headers, and support both `HH:MM:SS.mmm` and `MM:SS.mmm` WebVTT timestamps.
</Aside>

---

## Soft Subtitles (`--merge`) vs Hardcoded (`--burn`)

Subtitle CLI **never modifies your original media file**. Both options write a new video alongside the generated subtitle file.

### Soft Subtitles (`--merge`)

Muxes the subtitle file as a selectable subtitle track with zero video re-encoding (`vcodec=copy`, `acodec=copy`), making it near-instant:

```bash
subtitle lecture.mp4 --format srt --merge
# Writes: ./lecture.srt and ./lecture_subtitled.mp4
```

Container codecs are selected automatically based on output extension:

| Container | Subtitle Codec |
|-----------|----------------|
| `.mp4`, `.m4v`, `.mov` | `mov_text` |
| `.mkv` | `srt` |
| `.webm` | `webvtt` |

### Hardcoded Subtitles (`--burn`)

Renders subtitles directly into video frames using FFmpeg's `subtitles` filter while preserving the original audio track (`acodec=copy`):

```bash
subtitle reel.mp4 --format srt --max-len 16 --split-on-word --burn
# Writes: ./reel.srt and ./reel_burned.mp4
```

<Aside type="caution">
`--merge` and `--burn` are mutually exclusive. Because `--burn` re-encodes the video stream to draw subtitles into each frame, it takes longer than `--merge`.
</Aside>
