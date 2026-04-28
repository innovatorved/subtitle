# Subtitle Generator

> AI-powered subtitle generation using Whisper for accurate speech-to-text transcription.

[![PyPI version](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🎯 **Multi-format output** - VTT, SRT, TXT, JSON, LRC, ASS, TTML
- 🚀 **Fast processing** - Powered by whisper.cpp for high-performance inference
- 📦 **Batch processing** - Process multiple videos at once
- 🔄 **Video embedding** - Embed subtitles directly into videos
- 🌍 **Multilingual** - Support for multiple languages

## Installation

```bash
pip install subtitle-generator
```

### Prerequisites

This package shells out to the [`whisper.cpp`](https://github.com/ggml-org/whisper.cpp)
`whisper-cli` binary. It is **not bundled in the wheel** (whisper.cpp is per-OS
native code), so you need to provide it once.

- **FFmpeg** is required for video/audio processing:
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg

  # Windows (via chocolatey)
  choco install ffmpeg
  ```

- **whisper-cli** (the whisper.cpp transcription binary). The recommended
  setup is one command, run once after `pip install`:

  ```bash
  subtitle setup-whisper
  ```

  This clones the project's compatible whisper.cpp fork into your user
  data directory (e.g. `~/Library/Application Support/subtitle-generator/`
  on macOS) and builds it with CMake. Every subsequent `subtitle <video>`
  invocation auto-discovers the binary — no env vars, no PATH editing.

  Build prerequisites for `setup-whisper`:

  ```bash
  # macOS
  xcode-select --install     # provides clang++ + make
  brew install cmake ffmpeg

  # Linux (Debian/Ubuntu)
  sudo apt-get install -y build-essential cmake git ffmpeg

  # Windows
  # Install Visual Studio Build Tools, CMake, Git for Windows.
  ```

  The CLI auto-discovers the binary in this order:
  1. `--whisper-binary /path/to/whisper-cli`
  2. `SUBTITLE_WHISPER_BINARY` environment variable
  3. The binary installed by `subtitle setup-whisper` (preferred over PATH)
  4. `whisper-cli` / `whisper-cpp` / `main` on your `PATH`
  5. `./binary/whisper-cli` relative to the current directory (legacy)

  Note: Homebrew's `whisper-cpp` formula (currently 1.8.4) dropped the
  `-vi` flag and only accepts pre-extracted audio (`flac/mp3/ogg/wav`),
  so it is **not** sufficient for this package's "pass a video, get
  subtitles" UX. Use `subtitle setup-whisper` to build a compatible
  binary instead.

## Quick Start

```bash
# Generate subtitles (VTT format)
subtitle video.mp4

# Generate SRT format
subtitle video.mp4 --format srt

# Embed subtitles into video
subtitle video.mp4 --merge

# Use a larger model for better accuracy
subtitle video.mp4 --model large
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `subtitle <video>` | Generate subtitles for a video |
| `subtitle models --list` | List available Whisper models |
| `subtitle models --download <model>` | Download a specific model |
| `subtitle batch --input-dir <dir>` | Batch process multiple videos |
| `subtitle formats` | Show supported output formats |

## Options

| Option | Description |
|--------|-------------|
| `--model`, `-m` | Model to use: tiny, base, small, medium, large |
| `--format`, `-f` | Output format: vtt, srt, txt, json, lrc, ass, ttml |
| `--merge` | Embed subtitles into the video file |
| `--threads`, `-t` | Number of processing threads |
| `--verbose`, `-v` | Enable verbose output |

## Python API

```python
from subtitle_generator.core import SubtitleGenerator, WhisperCppTranscriber
from subtitle_generator.models import ModelManager

transcriber = WhisperCppTranscriber(binary_path="./binary/whisper-cli")
generator = SubtitleGenerator(transcriber=transcriber, model_manager=ModelManager())

result = generator.generate(
    input_path="video.mp4",
    model_name="base",
    output_format="srt",
    output_dir="data",
)
print(f"Subtitles saved to: {result.output_path}")
```

## Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~75MB | ⚡⚡⚡⚡ | ⭐⭐ |
| `base` | ~140MB | ⚡⚡⚡ | ⭐⭐⭐ |
| `small` | ~460MB | ⚡⚡ | ⭐⭐⭐⭐ |
| `medium` | ~1.5GB | ⚡ | ⭐⭐⭐⭐⭐ |
| `large` | ~3GB | 🐢 | ⭐⭐⭐⭐⭐ |

> **Tip:** Use `.en` models (e.g., `base.en`) for English-only content for faster processing.

## Links

- 📖 [Documentation](https://github.com/innovatorved/subtitle#readme)
- 🐛 [Issue Tracker](https://github.com/innovatorved/subtitle/issues)
- 📦 [Source Code](https://github.com/innovatorved/subtitle)

## License

MIT License - see [LICENSE](https://github.com/innovatorved/subtitle/blob/master/LICENSE) for details.
