---
title: Subtitle CLI
description: Fast, offline, AI-powered subtitle generation for video and audio files powered by whisper.cpp.
template: splash
hero:
  tagline: Generate, convert, embed, and burn accurate subtitles for any video or audio file locally using whisper.cpp. Zero cloud lock-in, modular Python API, and parallel batch processing.
  actions:
    - text: Get Started
      link: /docs/getting-started
      icon: right-arrow
      variant: primary
    - text: CLI Reference
      link: /docs/cli-reference
      icon: external
      variant: minimal
---

## What is Subtitle CLI?

Subtitle CLI (`subtitle-generator`) is a lightweight, modular command-line tool and Python library that wraps [whisper.cpp](https://github.com/ggml-org/whisper.cpp) ([custom fork with native video input](https://github.com/innovatorved/whisper.cpp)) to transcribe local media files, URLs, and entire folders into clean subtitles — completely offline on your own machine.

Install it via `pip`, run `subtitle setup-whisper` once, and generate **VTT**, **SRT**, **TXT**, **JSON**, **LRC**, or **CSV** subtitles from any video or audio file in seconds.

---

## Core Capabilities

<CardGrid>
  <Card title="One-Command Transcription">
    Point `subtitle` at any video, audio file, HTTP/HTTPS URL, or Google Drive link. Original media files are never modified.
  </Card>
  <Card title="Soft Mux & Hard Burn">
    Embed selectable subtitle tracks (`--merge`) with automatic container codec detection, or hardcode subtitles (`--burn`) while preserving the original audio stream.
  </Card>
  <Card title="Parallel Batch Processing">
    Process entire directories concurrently with configurable `--workers`, `--threads`, `--resume` state recovery, and Markdown summary reports.
  </Card>
  <Card title="Modular Python SDK">
    Plug `SubtitleGenerator`, `WhisperCppTranscriber`, `BatchProcessor`, `VideoProcessor`, `ModelManager`, and `SubtitleFormatterFactory` directly into your own apps.
  </Card>
</CardGrid>

---

## Architecture

Subtitle CLI separates CLI orchestration, model caching, transcription strategies, FFmpeg video operations, and subtitle formatters into clean, independently testable modules.

```
CLI (`subtitle ...`) or Python SDK (`subtitle_generator`)
  │
  ├── ModelManager          → Downloads & caches GGML models in per-OS cache dir
  ├── Downloader            → Fetches HTTP(S) & Google Drive media into temp storage
  ├── WhisperCppTranscriber → Invokes `whisper-cli` (-vi native or FFmpeg WAV fallback)
  ├── VideoProcessor        → Soft-muxes (--merge) or hard-burns (--burn) via FFmpeg
  ├── BatchProcessor        → ThreadPoolExecutor + .batch_state.json + batch_report.md
  └── Formatters            → Parse & convert VTT, SRT, CSV, LRC, and TXT
```

---

## Quick Links

<CardGrid>
  <LinkCard title="Getting Started" href="/docs/getting-started" description="Install subtitle-generator, build whisper-cli once on macOS, Linux, or Windows, and generate your first subtitle." />
  <LinkCard title="CLI Reference" href="/docs/cli-reference" description="Complete reference for every command, flag, short-form caption option, and translation workflow." />
  <LinkCard title="Batch Processing" href="/docs/batch-processing" description="Transcribe directories in parallel with worker tuning, resume support, and Markdown reports." />
  <LinkCard title="Python API" href="/docs/python-api" description="Embed subtitle generation, format conversion, and custom strategies in Python." />
</CardGrid>

---

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.9+ |
| Engine | `whisper.cpp` (`whisper-cli` compiled via `subtitle setup-whisper`) |
| Video / Audio | FFmpeg (`ffmpeg-python`) |
| Models | GGML Whisper models (`tiny`, `base`, `small`, `medium`, `large-v3`, `turbo`, quantized) |
| Formats | `vtt`, `srt`, `txt`, `json`, `lrc`, `csv` |
| Distribution | PyPI (`pip install subtitle-generator`) |
| License | MIT |
