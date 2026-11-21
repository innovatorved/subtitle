---
title: Getting Started
description: Install subtitle-generator, build the whisper-cli binary once, and transcribe your first video or audio file.
---

## Prerequisites

`subtitle setup-whisper` compiles `whisper.cpp` locally for maximum native performance (Apple Metal/Accelerate on macOS, native SIMD/CPU on Linux and Windows). You need `git`, `cmake`, a C++ compiler, and `ffmpeg` on your `PATH`.

<Tabs>
  <TabItem label="macOS">
```bash
xcode-select --install
brew install cmake ffmpeg
```
  </TabItem>
  <TabItem label="Linux (Debian / Ubuntu)">
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git ffmpeg
```
  </TabItem>
  <TabItem label="Windows">
Install **Git for Windows**, **CMake**, **Visual Studio Build Tools** (C++ workload), and **FFmpeg** (for example via `winget install Gyan.FFmpeg Kitware.CMake Git.Git`).
  </TabItem>
</Tabs>

---

## Installation

<Steps>
1. **Install the Python package from PyPI**

```bash
pip install subtitle-generator
```

2. **Build `whisper-cli` (one-time setup)**

```bash
subtitle setup-whisper
```

This clones `innovatorved/whisper.cpp` (`develop` branch with native `-vi` video input support), compiles a static Release binary, and installs it into your per-OS user data directory. It is auto-discovered on every future run.

3. **Verify your installation**

```bash
subtitle --version
subtitle models --list
```
</Steps>

<Aside type="tip">
Already have a stock `whisper-cli` binary installed? Point `--whisper-binary /path/to/whisper-cli` or `SUBTITLE_WHISPER_BINARY` at it. If the binary does not support `-vi`, Subtitle CLI automatically extracts a temporary 16 kHz mono WAV via FFmpeg and cleans it up afterwards.
</Aside>

---

## Your First Subtitle

Generate a WebVTT (`.vtt`) subtitle file in your current directory:

```bash
subtitle video.mp4
```

On first run, the default `base` model (~140 MB) is automatically downloaded to your user cache directory with a progress bar.

Generate an SRT file using the fast, high-accuracy `turbo` (`large-v3-turbo`) model:

```bash
subtitle video.mp4 --model turbo --format srt
```

Embed soft subtitles into a copy of the video (original video is never touched):

```bash
subtitle video.mp4 --merge --format srt
# Creates ./video.srt and ./video_subtitled.mp4
```

Burn hardcoded subtitles directly into the video stream (audio track preserved):

```bash
subtitle video.mp4 --burn --format srt
# Creates ./video.srt and ./video_burned.mp4
```

---

## Storage & Environment Variables

Subtitle CLI stores downloaded models and the built `whisper-cli` binary in standard per-OS user directories so it works cleanly from any working directory.

| Resource | macOS | Linux | Windows |
|----------|-------|-------|---------|
| Models cache | `~/Library/Caches/subtitle-generator/models` | `${XDG_CACHE_HOME:-~/.cache}/subtitle-generator/models` | `%LOCALAPPDATA%\subtitle-generator\Cache\models` |
| `setup-whisper` data & binary | `~/Library/Application Support/subtitle-generator` | `${XDG_DATA_HOME:-~/.local/share}/subtitle-generator` | `%LOCALAPPDATA%\subtitle-generator` |

Override any location with environment variables:

| Variable | Purpose |
|----------|---------|
| `SUBTITLE_WHISPER_BINARY` | Explicit path to `whisper-cli` |
| `SUBTITLE_MODELS_DIR` | Custom directory for cached GGML models |
| `SUBTITLE_DATA_DIR` | Custom directory for `setup-whisper` source & binary |
