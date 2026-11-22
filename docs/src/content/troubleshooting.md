---
title: Troubleshooting
description: Fast diagnostics with subtitle doctor, prebuilt binaries, FFmpeg fallback, Silero VAD, and performance tips.
---

## Start with `subtitle doctor`

Run `subtitle doctor` first to inspect your OS, Python version, GPU acceleration, `whisper-cli` features, `ffmpeg`/`ffprobe`, hardware encoders, disk space, and optional extras:

```bash
subtitle doctor
subtitle doctor --json
```

---

## "Could not find the whisper-cli binary"

Run the one-time installer:

```bash
subtitle setup-whisper
```

- Downloads a **SHA-256 verified prebuilt binary** for macOS (`arm64`/`x86_64`), Linux (`x86_64`/`arm64`), or Windows (`x64`) in ~2 seconds — zero compilers needed.
- If you want to compile from source with a specific GPU backend (CUDA, Vulkan, Metal, or CPU):

```bash
subtitle setup-whisper --from-source --gpu cuda
```

---

## "FFmpeg binary not found on PATH"

Install `ffmpeg` via your OS package manager (`brew install ffmpeg`, `sudo apt-get install ffmpeg`, `winget install Gyan.FFmpeg`) **or** install the bundled static fallback:

```bash
pip install 'subtitle-generator[ffmpeg]'
```

---

## Silence Hallucinations or Slow Transcription

- **Silero VAD is ON by default** in v4.0 (`ggml-silero-v5.1.2.bin`, ~864 KB auto-downloaded), which eliminates silence hallucinations and speeds up transcription 2–3×. Pass `--no-vad` to disable it.
- Use `--scrub` or `--preset netflix` to strip any remaining Whisper repetition loops.
- For fast high-accuracy local runs, use `--model large-v3-turbo-q5_0` or `--model turbo`.
- For ultra-fast cloud transcription on low-spec hardware, install `pip install 'subtitle-generator[cloud]'` and run `--backend groq`.

---

## Still Stuck?

Open an issue at [github.com/innovatorved/subtitle/issues](https://github.com/innovatorved/subtitle/issues) with the output of `subtitle doctor` and `subtitle video.mp4 --verbose`.
