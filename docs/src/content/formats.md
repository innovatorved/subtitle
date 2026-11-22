---
title: Formats, Karaoke & Netflix Lint
description: Supported subtitle formats, word-highlighted Karaoke ASS captions, Netflix/BBC/Reels broadcast presets, and soft/hard embedding.
---

## Supported Subtitle Formats

Emit one or **multiple formats in a single transcription pass** (`--format srt,vtt,ass`):

| Format | Flag | Description | Convertible via `subtitle convert` |
|--------|------|-------------|-------------------------------------|
| **WebVTT** | `vtt` | Web video standard (`HH:MM:SS.mmm`) *(default)* | Yes |
| **SubRip** | `srt` | Universal desktop & editor format (`HH:MM:SS,mmm`) | Yes |
| **ASS / SSA** | `ass` | Advanced styled & word-highlighted **Karaoke** captions | Yes |
| **TTML** | `ttml` | W3C / EBU-TT XML broadcast streaming standard | Yes |
| **JSON** | `json` | Structured JSON with word-level timestamps & confidence | Yes |
| **CSV** | `csv` | Millisecond-aligned `start,end,text` spreadsheet | Yes |
| **LRC** | `lrc` | Synchronized lyrics format (`[mm:ss.xx]`) | Yes |
| **Plain Text** | `txt` | Clean transcript without timestamps | Yes |

---

## What is Karaoke (`--style karaoke`)?

Think of **Instagram Reels, TikTok, and YouTube Shorts** where bold captions appear on screen and **each word highlights in bright yellow at the exact millisecond the speaker says it**.

- Standard `.srt` / `.vtt` files only store sentence-level start/end times.
- `.ass` files support **word-level karaoke tags** (`{\kf80}Hello {\kf110}world`) driven by Whisper's word timestamps (`-ojf`).
- Run one command to generate and burn CapCut-style animated captions locally:

```bash
subtitle reel.mp4 --burn --style karaoke --preset reels
```

Available `--style` presets for `.ass` and `--burn`:

| Style | Visual Look | Best For |
|-------|-------------|----------|
| `clean` | Crisp white sans-serif with black outline & drop shadow | YouTube, tutorials, courses |
| `box` | Semi-transparent dark rounded box behind text | High-contrast accessibility |
| `karaoke` | Bold high-contrast yellow word-by-word highlight | TikTok, Reels, YouTube Shorts |
| `cinema` | Subtle warm off-white lower-third styling | Documentaries, films |

---

## What is Netflix Lint (`--preset` & `subtitle lint`)?

Streaming platforms and broadcasters enforce strict readability rules so viewers never experience eye strain or miss text before a cut:

| Preset / Standard | Max CPL (Chars/Line) | Max Lines | Max Reading Speed | Cue Duration |
|-------------------|----------------------|-----------|-------------------|--------------|
| `netflix` | **42** | 2 | **20 CPS** | 0.83s – 7.0s |
| `netflix-kids` | **42** | 2 | **17 CPS** | 0.83s – 7.0s |
| `bbc` | **37** | 2 | **17 CPS** | 1.0s – 6.0s |
| `reels` / `shorts` | **18** | 1 | **24 CPS** | 0.3s – 2.5s |

- **`--preset netflix`** automatically reflows raw Whisper output to obey CPL, balances 2-line pyramids on natural punctuation/linguistic breaks, prevents overlaps, and scrubs silence hallucinations.
- **`subtitle lint file.srt --standard netflix`** audits any subtitle file and reports every `MAX_CPL`, `MAX_LINES`, `MAX_CPS`, `MIN_DURATION`, `MAX_DURATION`, and `OVERLAP` issue (exiting with code `1` on errors for CI/QC pipelines).

---

## Soft Mux (`--merge`) vs Hard Burn (`--burn`)

Subtitle CLI **never modifies your original media file**.

- **`--merge`**: Stream-copies video & audio with zero re-encoding (instant) and auto-picks container subtitle codec (`mov_text` for MP4/MOV/M4V, `srt` for MKV, `webvtt` for WebM).
- **`--burn`**: Hardcodes subtitles into video frames while preserving the original audio stream (`-c:a copy`), automatically using hardware H.264 encoders (`h264_videotoolbox` on Apple Silicon, `h264_nvenc` on NVIDIA) with automatic `libx264` fallback.
