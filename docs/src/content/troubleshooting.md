---
title: Troubleshooting
description: Solutions for common setup, whisper-cli, FFmpeg, model download, and performance issues.
---

## "Could not find the whisper-cli binary"

Run the one-time setup command to compile and install `whisper-cli` into your user data directory:

```bash
subtitle setup-whisper
```

Make sure `git`, `cmake`, a C++ compiler, and `ffmpeg` are on your `PATH`:

```bash
# macOS
xcode-select --install && brew install cmake ffmpeg

# Linux (Debian / Ubuntu)
sudo apt-get install -y build-essential cmake git ffmpeg
```

If you already have a `whisper-cli` binary elsewhere, point to it explicitly:

```bash
export SUBTITLE_WHISPER_BINARY=/path/to/whisper-cli
# or per command:
subtitle video.mp4 --whisper-binary /path/to/whisper-cli
```

<Aside type="note">
Upstream Homebrew `whisper-cpp` 1.8.x dropped the `-vi` video-input flag. `subtitle setup-whisper` builds the compatible `innovatorved/whisper.cpp` fork with native `-vi` support. If you point `--whisper-binary` at a stock binary without `-vi`, Subtitle CLI automatically falls back to extracting a temporary 16 kHz mono WAV via FFmpeg.
</Aside>

---

## Slow Transcription or High CPU Usage

- Use a smaller or quantized model: `--model tiny`, `--model base.en`, or `--model large-v3-turbo-q5_0`
- Tune thread count: `--threads 8` (for single files)
- For batch jobs, balance workers and threads: `subtitle batch -i ./videos --workers 2 --threads 4`
- For English-only audio, prefer `.en` models (`base.en`, `small.en`) for faster, more accurate output

---

## Out of Memory on Large Videos

Switch to a smaller/quantized model (`--model small-q5_1` or `--model large-v3-turbo-q5_0`), or split very long recordings into chunks with FFmpeg:

```bash
ffmpeg -i large_video.mp4 -t 00:30:00 -c copy part1.mp4
```

---

## Model Download Fails

Downloads retry automatically with exponential backoff and write atomically to `.part` files so interrupted downloads never leave corrupt models behind. To test a download directly:

```bash
subtitle models --download tiny
```

You can also download any `ggml-*.bin` file manually from [ggerganov/whisper.cpp on Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main) and drop it into your models cache directory (printed at the top of `subtitle models --list`).

---

## Still Stuck?

Open an issue at [github.com/innovatorved/subtitle/issues](https://github.com/innovatorved/subtitle/issues) with your OS, Python version, and the output of `subtitle video.mp4 --verbose`.
