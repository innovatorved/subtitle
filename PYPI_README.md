# Subtitle Generator

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Docs](https://img.shields.io/badge/docs-subtitle.vedgupta.in-F97316)](https://subtitle.vedgupta.in)
[![Version](https://img.shields.io/badge/version-v4.1.1-18181b)](https://github.com/innovatorved/subtitle/releases/tag/v4.1.1)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Full Documentation:** **[https://subtitle.vedgupta.in](https://subtitle.vedgupta.in)**

**Industry-standard, cross-platform AI subtitle generation, styling, QC, and embedding toolkit.**  
Runs locally on macOS (Apple Silicon Metal), Linux (CPU / CUDA / Vulkan), Windows, and Docker — with optional `faster-whisper` and OpenAI/Groq cloud backends.

## Install

```bash
pip install subtitle-generator
subtitle video.mp4              # zero-config: auto-installs prebuilt whisper-cli + model on first run!
```

Optional extras:

```bash
pip install 'subtitle-generator[yt]'              # YouTube / TikTok / Vimeo URLs via yt-dlp
pip install 'subtitle-generator[ffmpeg]'          # Bundled static ffmpeg fallback
pip install 'subtitle-generator[gdrive]'          # Google Drive URLs via gdown
pip install 'subtitle-generator[faster-whisper]'  # CTranslate2 NVIDIA GPU backend
pip install 'subtitle-generator[cloud]'           # OpenAI / Groq Whisper API + LLM translation
pip install 'subtitle-generator[translate]'       # Offline local subtitle translation (Argos)
pip install 'subtitle-generator[all]'             # Everything
```

## Highlights (v4.0)

- **Zero-Friction Cross-Platform Setup:** Prebuilt SHA-256 verified `whisper-cli` binaries with CMake + GPU source-build fallback and `subtitle doctor` diagnostics.
- **Silero VAD + Live Progress:** Voice Activity Detection enabled by default (2–3× faster, eliminates silence hallucinations) with real-time percentage progress streaming.
- **Broadcast & Creator Presets:** `--preset netflix|bbc|reels` CPL/CPS reflow, balanced line wrapping, hallucination scrubber, and `subtitle lint` QC validator.
- **Styled `.ass` & Word-Highlighted Karaoke Captions:** `--burn --style clean|box|karaoke|cinema` with hardware H.264 encoder auto-detection (`videotoolbox` / `nvenc`).
- **One-Pass Multi-Format Export:** `--format srt,vtt,ass,ttml,json` in a single transcription run.
- **Complete Toolkit:** `doctor`, `batch` (`--recursive`, `--resume`, `--merge`, `--burn`), `watch`, `convert`, `lint`, `shift`, `translate`, `config`, and `--json` output.

## Quick Examples

```bash
subtitle video.mp4 --format srt,vtt,ass --preset netflix
subtitle reel.mp4 --burn --style karaoke --preset reels
subtitle video.mp4 --merge --format srt
subtitle lint video.srt --standard netflix
subtitle shift video.srt --offset +500 -o synced.srt
subtitle translate video.srt --to es
subtitle batch -i ./videos -o ./subs --recursive --preset netflix
subtitle watch ./incoming -o ./subs --model turbo
```

## Links

- **Documentation:** [https://subtitle.vedgupta.in](https://subtitle.vedgupta.in)
- **Getting Started:** [https://subtitle.vedgupta.in/docs/getting-started](https://subtitle.vedgupta.in/docs/getting-started)
- **CLI Reference:** [https://subtitle.vedgupta.in/docs/cli-reference](https://subtitle.vedgupta.in/docs/cli-reference)
- **Formats, Karaoke & Netflix Lint:** [https://subtitle.vedgupta.in/docs/formats](https://subtitle.vedgupta.in/docs/formats)
- **Source Code:** [https://github.com/innovatorved/subtitle](https://github.com/innovatorved/subtitle)
- **Issues:** [https://github.com/innovatorved/subtitle/issues](https://github.com/innovatorved/subtitle/issues)
