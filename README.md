# Subtitle Generator

[![PyPI version](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://static.pepy.tech/badge/subtitle-generator)](https://pepy.tech/project/subtitle-generator)

> AI-powered subtitle generation using Whisper for accurate speech-to-text transcription.

**Key Features:**

- 🎯 **Multi-format output** - VTT, SRT, TXT, JSON, LRC, ASS, TTML
- 🚀 **Fast processing** - Powered by whisper.cpp for high-performance inference
- 📦 **Batch processing** - Process multiple videos at once
- 🔄 **Video embedding** - Embed subtitles directly into videos
- 🌍 **Multilingual** - Support for multiple languages
- 🔓 **Open-source** - Freely available for use, modification, and distribution

## Installation

### Quick Install (PyPI)

```bash
pip install subtitle-generator
```

> **Note:** FFmpeg is required. Install via: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Ubuntu)

### Development Setup

For contributors or if you need to build whisper.cpp from source:

#### Prerequisites

- `git`, `make`, `cmake`
- `ffmpeg` (Required for video processing)
- `conda` (Anaconda or Miniconda)

#### Setup

1. **Clone and setup Whisper.cpp:**
   ```bash
   ./setup_whisper.sh
   ```

2. **Create and activate conda environment:**
   ```bash
   conda env create -f environment.yml
   conda activate subtitle
   ```

## Usage

### Generate Subtitles

```bash
# Basic usage (generates VTT subtitle file)
python subtitle.py video.mp4

# Generate and embed subtitles into video
python subtitle.py video.mp4 --merge

# Use a specific model
python subtitle.py video.mp4 --model base

# Generate SRT format
python subtitle.py video.mp4 --format srt

# From URL
python subtitle.py "https://example.com/video.mp4"
```

### Model Management

```bash
# List all available models
python subtitle.py models --list

# Download a specific model
python subtitle.py models --download large
```

### View Supported Formats

```bash
python subtitle.py formats
```

### Options

| Option | Description |
|--------|-------------|
| `--model`, `-m` | Model to use (default: base) |
| `--format`, `-f` | Output format: vtt, srt, txt, json, lrc (default: vtt) |
| `--merge` | Embed subtitles into video |
| `--threads`, `-t` | Number of threads (default: 4) |
| `--verbose`, `-v` | Verbose output |

### Available Models

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `tiny` | ~75MB | Fastest | Quick previews |
| `base` | ~140MB | Fast | General use (default) |
| `small` | ~460MB | Medium | Quality output |
| `medium` | ~1.5GB | Slow | Professional work |
| `large` | ~3GB | Slowest | Maximum accuracy |

> **Tip:** Use `.en` models (e.g., `base.en`) for English-only content.

## Documentation

- [Usage Examples](docs/example.md) - CLI and Python API examples
- [API Reference](docs/API.md) - Programmatic API documentation
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Contributing](CONTRIBUTING.md) - Contribution guidelines

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Reference & Credits

- [OpenAI Whisper](https://github.com/openai/whisper)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp)

## Author

- [Ved Gupta](https://www.github.com/innovatorved)

## Support

For support, email vedgupta@protonmail.com
