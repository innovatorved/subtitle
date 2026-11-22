---
title: Subtitle CLI
description: Industry-standard, cross-platform AI subtitle generation, styling, QC, and embedding toolkit powered by whisper.cpp.
template: splash
hero:
  tagline: Generate, reflow, lint, style, translate, embed, and burn broadcast & creator-grade subtitles on macOS, Linux, Windows, and Docker — locally or via optional cloud backends.
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

## What is Subtitle CLI (v4.0.0)?

Subtitle CLI (`subtitle-generator`) is an ultra-lightweight, production-ready command-line toolkit and Python SDK built around [whisper.cpp](https://github.com/ggml-org/whisper.cpp) ([custom fork with native `-vi` video input](https://github.com/innovatorved/whisper.cpp)), with optional `faster-whisper` and OpenAI/Groq cloud backends.

Install via `pip`, run `subtitle setup-whisper` once (downloads a SHA-256 verified prebuilt binary in ~2 seconds with automatic source-build fallback), and generate **VTT**, **SRT**, **ASS** (styled & word-highlighted karaoke), **TTML**, **JSON**, **LRC**, **CSV**, or **TXT** subtitles in a single pass.

---

## Core Capabilities

<CardGrid>
  <Card title="Silero VAD & Live Progress">
    Voice Activity Detection (`--vad`, on by default) strips silence before decoding — eliminating Whisper hallucinations and speeding up transcription 2–3× with live percentage progress.
  </Card>
  <Card title="Broadcast QC & Presets">
    Built-in `--preset netflix`, `bbc`, and `reels` presets enforce CPL, CPS, balanced 2-line wrapping, and hallucination scrubbing. Validate any subtitle file with `subtitle lint`.
  </Card>
  <Card title="Karaoke & Styled Burn">
    Generate CapCut-style word-highlighted TikTok/Reels captions (`--burn --style karaoke --preset reels`) with hardware H.264 encoder auto-detection (`videotoolbox` / `nvenc`).
  </Card>
  <Card title="Complete Subtitle Toolkit">
    Includes `doctor`, `batch` (`--recursive`, `--resume`, `--merge`, `--burn`), `watch`, `convert`, `lint`, `shift`, `translate`, `config`, and `--json` output.
  </Card>
</CardGrid>

---

## Architecture

```
CLI (`subtitle ...`) or Python SDK (`subtitle_generator`)
  │
  ├── Doctor & Config       → OS/GPU/FFmpeg/whisper-cli diagnostics + config.toml
  ├── ModelManager          → Per-dir cache, Range resume, SHA-256, Silero VAD auto-fetch
  ├── Downloader            → Direct HTTP(S), Google Drive ([gdrive]), YouTube/TikTok ([yt])
  ├── Transcriber Backends  → whisper.cpp (default), faster-whisper, OpenAI / Groq cloud
  ├── Post-Process & QC     → Netflix/BBC/Reels CPL & CPS reflow, hallucination scrubber, lint, shift
  ├── Formatters            → VTT, SRT, ASS (clean/box/karaoke/cinema), TTML, JSON, CSV, LRC, TXT
  ├── VideoProcessor        → Direct FFmpeg subprocess (no ffmpeg-python), HW H.264, Windows-safe paths
  └── Batch & Watcher       → Smart CPU thread budgeting, recursive mirroring, folder watch
```

---

## Quick Links

<CardGrid>
  <LinkCard title="Getting Started" href="/docs/getting-started" description="Install subtitle-generator, download prebuilt whisper-cli, run subtitle doctor, and create your first subtitle." />
  <LinkCard title="CLI Reference" href="/docs/cli-reference" description="Every command and flag: transcribe, doctor, lint, shift, translate, watch, batch, convert, and config." />
  <LinkCard title="Formats, Karaoke & Netflix Lint" href="/docs/formats" description="Learn how word-highlighted Karaoke ASS captions and Netflix/BBC QC linting work." />
  <LinkCard title="Python API" href="/docs/python-api" description="Embed transcription, presets, linting, shifting, and multi-backend workflows in Python." />
</CardGrid>

---

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.9–3.13 (core deps: `tqdm` + stdlib only) |
| Default Engine | `whisper.cpp` (prebuilt Metal / Linux / Windows binaries + CMake fallback) |
| Optional Backends | `faster-whisper` (`[faster-whisper]`), OpenAI & Groq (`[cloud]`) |
| Video / Audio | Direct FFmpeg/FFprobe subprocess (`[ffmpeg]` static fallback) |
| Formats | `vtt`, `srt`, `ass`, `ttml`, `json`, `csv`, `lrc`, `txt` |
| Distribution | PyPI, Docker, Homebrew |
| License | MIT |
