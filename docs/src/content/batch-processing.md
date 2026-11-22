---
title: Batch Processing & Folder Watch
description: Transcribe entire directories of video and audio files in parallel with recursive mirroring, resume, presets, and automated folder watching.
---

## Parallel Batch Processing (`subtitle batch`)

`subtitle batch` scans a directory for video and audio files and processes them concurrently with **smart CPU thread budgeting** (`threads = max(1, cpu_count // workers)`), atomic `.batch_state.json` resume support, and a Markdown `batch_report.md` summary.

```bash
subtitle batch -i ./videos -o ./subtitles --recursive --model turbo --format srt --preset netflix --workers 2
```

### Batch Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--input-dir DIR` | `-i` | *(required)* | Directory containing video/audio files |
| `--output-dir DIR` | `-o` | same as input | Destination directory (mirrors subdirectories when `--recursive`) |
| `--recursive` | `-R` | `False` | Recursively scan subdirectories (case-insensitive extensions) |
| `--workers N` | `-w` | `2` | Number of parallel worker threads |
| `--threads N` | `-t` | auto | `whisper-cli` threads per worker (auto-budgeted across workers) |
| `--model MODEL` | `-m` | `base` | Whisper model (`tiny`, `base`, `small`, `turbo`, `large-v3`, etc.) |
| `--format FMT` | `-f` | `vtt` | Output format (`vtt`, `srt`, `ass`, `ttml`, `json`, `csv`, `lrc`, `txt`) |
| `--backend NAME` | | `whisper.cpp` | Backend (`whisper.cpp`, `faster-whisper`, `openai`, `groq`) |
| `--preset NAME` | | `None` | Broadcast/creator reflow preset (`netflix`, `bbc`, `reels`) |
| `--no-vad` | | `False` | Disable Silero VAD |
| `--merge` / `--burn` | | `False` | Soft-mux or hard-burn subtitles into copies of each video |
| `--style STYLE` | | `clean` | ASS/burn style (`clean`, `box`, `karaoke`, `cinema`) |
| `--resume` | `-r` | `False` | Skip files already recorded in `.batch_state.json` |
| `--extensions LIST` | `-e` | all video & audio | Comma-separated extensions to include |

---

## Automated Folder Watch (`subtitle watch`)

Continuously watch an incoming folder (great for Plex/Jellyfin, studio dropboxes, or content pipelines). Uses a **file-size stability check** so partially copied files are never processed prematurely:

```bash
subtitle watch ./incoming -o ./subs --model turbo --format srt --preset netflix --recursive
```
