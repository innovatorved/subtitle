---
title: Getting Started
description: Install subtitle-generator v4.0.0, get prebuilt whisper-cli, verify with subtitle doctor, and transcribe your first video or URL.
---

## Installation

`subtitle-generator` v4.0.0 has an **ultra-light core** (`tqdm` + Python stdlib only) and installs prebuilt `whisper-cli` binaries in ~2 seconds with zero compiler setup required on macOS, Linux, and Windows.

<Steps>
1. **Install from PyPI**

```bash
pip install subtitle-generator
```

2. **Run immediately (zero extra setup required!)**

```bash
subtitle video.mp4
```

On first run, `subtitle` automatically downloads the SHA-256 verified prebuilt `whisper-cli` binary for your OS/CPU (`macOS`, `Linux`, `Windows`) in ~2 seconds along with the requested Whisper & Silero VAD models — zero compilers or extra setup commands needed.

3. **Optional: Verify or custom-compile**

```bash
subtitle doctor                           # check OS, GPU, whisper-cli, ffmpeg & extras
subtitle setup-whisper --from-source      # optional: custom local CMake build (e.g. --gpu cuda)
```
</Steps>

### Optional Extras

Install only what you need:

```bash
pip install 'subtitle-generator[yt]'              # YouTube, TikTok, Vimeo, X URLs via yt-dlp
pip install 'subtitle-generator[ffmpeg]'          # Bundled static ffmpeg binary fallback
pip install 'subtitle-generator[gdrive]'          # Google Drive URLs via gdown
pip install 'subtitle-generator[faster-whisper]'  # CTranslate2 NVIDIA GPU backend
pip install 'subtitle-generator[cloud]'           # OpenAI / Groq Whisper API + LLM translation
pip install 'subtitle-generator[translate]'       # Local offline subtitle translation (Argos)
pip install 'subtitle-generator[all]'             # All extras
```

---

## Your First Subtitle

```bash
# 1. Default VTT with Silero VAD (auto-downloaded) + live progress
subtitle video.mp4

# 2. Netflix-compliant multi-format export in ONE pass
subtitle video.mp4 --model turbo --format srt,vtt,ass --preset netflix

# 3. Viral word-highlighted Karaoke captions burned into video (Reels / TikTok / Shorts)
subtitle reel.mp4 --burn --style karaoke --preset reels

# 4. Soft subtitles muxed cleanly into a copy of the video (instant, no re-encode)
subtitle video.mp4 --merge --format srt

# 5. Validate any subtitle file against Netflix / BBC rules
subtitle lint video.srt --standard netflix
```

---

## Persistent Configuration (`config.toml`)

Save your preferred model, format, preset, and burn style once:

```bash
subtitle config --init
```

This creates `~/.config/subtitle-generator/config.toml` (or `%APPDATA%\subtitle-generator\config.toml` on Windows). Project-local `.subtitle.toml` files override user config, and CLI flags always override both.

---

## Storage & Environment Variables

| Resource | macOS | Linux | Windows |
|----------|-------|-------|---------|
| Models cache | `~/Library/Caches/subtitle-generator/models` | `${XDG_CACHE_HOME:-~/.cache}/subtitle-generator/models` | `%LOCALAPPDATA%\subtitle-generator\Cache\models` |
| `setup-whisper` data & binary | `~/Library/Application Support/subtitle-generator` | `${XDG_DATA_HOME:-~/.local/share}/subtitle-generator` | `%LOCALAPPDATA%\subtitle-generator` |
| Config file | `~/.config/subtitle-generator/config.toml` | `${XDG_CONFIG_HOME:-~/.config}/subtitle-generator/config.toml` | `%APPDATA%\subtitle-generator\config.toml` |

Override any path with `SUBTITLE_WHISPER_BINARY`, `SUBTITLE_FFMPEG_BINARY`, `SUBTITLE_MODELS_DIR`, `SUBTITLE_DATA_DIR`, or `SUBTITLE_CONFIG_PATH`.
