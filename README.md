# Subtitle

Open-source subtitle generation for seamless content translation.

**Key Features:**

- **Open-source** - Freely available for use, modification, and distribution
- **Self-hosted** - Run on your own servers for enhanced control and privacy
- **AI-powered** - Leverage Whisper for accurate, natural-sounding subtitles
- **Multilingual** - Generate subtitles in a wide range of languages
- **Fast** - Uses whisper.cpp for high-performance inference

## Installation

### Prerequisites

Ensure you have the following installed:
- `git`, `make`, `cmake`
- `ffmpeg` (Required for video processing)
- `conda` (Anaconda or Miniconda)

### Setup

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
