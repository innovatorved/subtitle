---
title: CLI Reference
description: Complete command-line reference for subtitle generation, embedding, burning, format conversion, model management, and batch processing.
---

## Commands Overview

| Command | Description |
|---------|-------------|
| `subtitle <media>` | Transcribe a local video/audio file or URL and write subtitles |
| `subtitle <media> --merge` | Transcribe and embed selectable soft subtitles into a copy of the video |
| `subtitle <media> --burn` | Transcribe and burn hardcoded subtitles into a copy of the video |
| `subtitle batch --input-dir <dir>` | Process all media files in a directory in parallel |
| `subtitle convert <in> [out]` | Convert existing subtitle files between `vtt`, `srt`, `csv`, `lrc`, and `txt` |
| `subtitle models --list` | List all available models and show which are downloaded |
| `subtitle models --download <name>` | Pre-download a specific GGML model |
| `subtitle formats` | Display supported subtitle output formats |
| `subtitle setup-whisper` | One-time build and install of `whisper-cli` |

---

## Transcribe (`subtitle <media>`)

Transcribe a local file (`mp4`, `mkv`, `avi`, `mov`, `webm`, `mp3`, `wav`, `flac`, `m4a`, `ogg`, etc.) or an HTTP(S) / Google Drive URL.

```bash
subtitle video.mp4 [OPTIONS]
```

### Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--model MODEL` | `-m` | `base` | GGML Whisper model name (e.g. `tiny`, `base`, `small`, `turbo`, `large-v3`) |
| `--format FMT` | `-f` | `vtt` | Output format: `vtt`, `srt`, `txt`, `json`, `lrc`, `csv` |
| `--language CODE` | `-l` | `None` | Spoken language code (`en`, `es`, `fr`, `hi`, `auto`, etc.) |
| `--translate` | `-tr` | `False` | Translate spoken audio from source language to English |
| `--max-len N` | `-ml` | `0` | Maximum characters per subtitle cue (`0` = unlimited) |
| `--split-on-word` | `-sow` | `False` | Split segments on word boundaries (recommended with `--max-len`) |
| `--prompt TEXT` | | `None` | Initial prompt to guide domain terms, names, or punctuation |
| `--merge` | | `False` | Mux soft subtitles into `<name>_subtitled.<ext>` (mutually exclusive with `--burn`) |
| `--burn` | | `False` | Hardcode subtitles into `<name>_burned.<ext>` (mutually exclusive with `--merge`) |
| `--output-dir DIR` | `-o` | CWD | Directory where output files are written |
| `--threads N` | `-t` | `4` | Number of CPU threads for `whisper-cli` |
| `--processors N` | `-p` | `1` | Number of processors for `whisper-cli` |
| `--whisper-binary PATH` | | auto | Override the auto-discovered `whisper-cli` binary |
| `--models-dir DIR` | | cache | Override the GGML model cache directory |
| `--verbose` | `-v` | `False` | Enable debug logging and detailed progress output |
| `--version` | `-V` | | Print installed version and exit |

### Common Recipes

```bash
# Short-form / Reels / TikTok captions (max 16 chars, word-boundary split)
subtitle reel.mp4 --format srt --max-len 16 --split-on-word

# Translate Spanish speech to English SRT
subtitle entrevista.mp4 --language es --translate --format srt

# Guide proper nouns and technical jargon
subtitle talk.mp4 --model turbo --prompt "Whisper.cpp, FFmpeg, PyPI, Kubernetes"

# Transcribe directly from a URL into ~/subs
subtitle "https://example.com/lecture.mp4" --format vtt --output-dir ~/subs
```

---

## Models (`subtitle models`)

```bash
subtitle models --list
subtitle models --download turbo
subtitle models --download small.en --models-dir ./my-models
```

| Flag | Short | Description |
|------|-------|-------------|
| `--list` | `-l` | Show cache directory, all models, and `[x]` markers for downloaded ones |
| `--download MODEL` | `-d` | Download a model immediately with retry and atomic replacement |
| `--models-dir DIR` | | Custom cache directory |

---

## Convert (`subtitle convert`)

Convert existing subtitle files between `vtt`, `srt`, `csv`, `lrc`, and `txt`:

```bash
subtitle convert video.vtt video.srt
subtitle convert video.vtt --format srt
subtitle convert video.srt --format txt
subtitle convert transcript.raw out.vtt --source-format srt
```

| Argument / Flag | Description |
|-----------------|-------------|
| `input_path` | Path to the source subtitle file |
| `output_path` | Optional destination file path (inferred from `--format` if omitted) |
| `--format`, `-f` | Target format (`vtt`, `srt`, `csv`, `lrc`, `txt`) |
| `--source-format` | Explicit source format when the input extension is non-standard |

---

## Setup Whisper (`subtitle setup-whisper`)

```bash
subtitle setup-whisper
subtitle setup-whisper --force
subtitle setup-whisper --ref develop --no-pull
```

| Flag | Description |
|------|-------------|
| `--repo URL` | Override the default `whisper.cpp` fork URL |
| `--ref REF` | Git branch, tag, or commit to build (default: `develop`) |
| `--force` | Wipe and re-clone the source checkout before building |
| `--no-pull` | Skip `git fetch`/`pull` for offline rebuilds |
