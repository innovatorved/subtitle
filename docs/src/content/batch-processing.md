---
title: Batch Processing
description: Transcribe entire directories of videos in parallel with resume capability and Markdown summary reports.
---

## Overview

`subtitle batch` scans a directory for video files and processes them concurrently using a thread pool. It tracks per-file progress in `.batch_state.json`, lets you resume interrupted runs with `--resume`, and writes a formatted `batch_report.md` summary when finished.

```bash
subtitle batch --input-dir ./videos --output-dir ./subtitles --model turbo --format srt --workers 4
```

---

## Batch Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--input-dir DIR` | `-i` | *(required)* | Directory containing video files |
| `--output-dir DIR` | `-o` | same as input | Destination directory for subtitle files and report |
| `--workers N` | `-w` | `4` | Number of parallel worker threads |
| `--threads N` | `-t` | `4` | `whisper-cli` threads per worker |
| `--processors N` | `-p` | `1` | `whisper-cli` processors per worker |
| `--model MODEL` | `-m` | `base` | Whisper model to use |
| `--format FMT` | `-f` | `vtt` | Output subtitle format (`vtt`, `srt`, `txt`, `json`, `lrc`, `csv`) |
| `--language CODE` | `-l` | `None` | Spoken language code (`en`, `es`, `auto`, etc.) |
| `--translate` | `-tr` | `False` | Translate speech to English |
| `--max-len N` | `-ml` | `0` | Maximum cue length in characters |
| `--split-on-word` | `-sow` | `False` | Split segments on word boundaries |
| `--prompt TEXT` | | `None` | Initial prompt for vocabulary/style |
| `--resume` | `-r` | `False` | Skip files already recorded in `.batch_state.json` |
| `--extensions LIST` | `-e` | `mp4,mkv,avi,mov,webm,m4v,flv,wmv` | Comma-separated file extensions to include |
| `--whisper-binary PATH` | | auto | Override `whisper-cli` binary path |
| `--models-dir DIR` | | cache | Override model cache directory |

<Aside type="tip">
To avoid oversubscribing CPU cores during parallel runs, balance `--workers` and `--threads` so `workers × threads ≈ CPU cores`. For example, on an 8-core machine use `--workers 2 --threads 4` or `--workers 4 --threads 2`.
</Aside>

---

## Resuming Interrupted Batches

If a long batch run is cancelled (`Ctrl+C`) or a machine restarts, re-run the same command with `--resume`:

```bash
subtitle batch -i ./course_videos -o ./subs --model small --format srt --resume
```

- Completed and failed paths are persisted after every file in `<output-dir>/.batch_state.json`.
- When `--resume` is enabled, previously processed files are skipped automatically.
- Once a batch finishes with zero failures, `.batch_state.json` is cleaned up automatically.

---

## Summary Report

Every batch run writes `<output-dir>/batch_report.md` containing:

- Timestamp and total duration
- Counts of total, successful, failed, and skipped files
- Per-file table with status, duration, and output filename
