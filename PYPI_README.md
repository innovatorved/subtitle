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

- **FFmpeg** is required for video/audio processing:
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg

  # Windows (via chocolatey)
  choco install ffmpeg
  ```

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
from src.core.subtitle_gen import SubtitleGenerator

# Generate subtitles
generator = SubtitleGenerator()
result = generator.generate("video.mp4", format="srt")
print(f"Subtitles saved to: {result}")
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
