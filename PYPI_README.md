# Subtitle Generator

Generate subtitles for video/audio files using `whisper.cpp`.

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install subtitle-generator
subtitle setup-whisper          # one-time: clones + builds whisper-cli
```

`subtitle setup-whisper` needs `git`, `cmake`, a C++ compiler, and
`ffmpeg`:

```bash
# macOS
xcode-select --install && brew install cmake ffmpeg
# Linux
sudo apt-get install -y build-essential cmake git ffmpeg
# Windows
# Install Git, CMake, VS Build Tools, ffmpeg.
```

The built binary lands in your per-OS user data dir (e.g.
`~/Library/Application Support/subtitle-generator/bin/` on macOS) and is
auto-discovered on every subsequent run.

> `subtitle setup-whisper` builds `innovatorved/whisper.cpp` (`develop`), which includes `-vi` for direct video ingestion. If a stock `whisper-cli` without `-vi` is used instead, `subtitle-generator` automatically extracts 16 kHz mono WAV via `ffmpeg`.

## Usage

```bash
# VTT (default), output in current directory
subtitle video.mp4

# SRT
subtitle video.mp4 --format srt

# Generate SRT and embed soft subtitles into the video
# Writes ./video.srt and ./video_subtitled.mp4
subtitle video.mp4 --merge --format srt

# Burn (hardcode) subtitles into the video
# Writes ./video.srt and ./video_burned.mp4
subtitle video.mp4 --burn --format srt

# Fast high-accuracy model (large-v3-turbo) or full large-v3
subtitle video.mp4 --model turbo
subtitle video.mp4 --model large

# Specify language or translate to English
subtitle video.mp4 --language es --translate

# Short-form / TikTok / Reels captions (word-boundary splitting)
subtitle video.mp4 --format srt --max-len 16 --split-on-word

# Initial prompt for vocabulary / proper nouns
subtitle video.mp4 --prompt "Whisper.cpp, PyPI, FFmpeg"

# Convert between subtitle formats (vtt, srt, csv, lrc, txt)
subtitle convert video.vtt video.srt

# Custom output directory
subtitle /path/to/video.mp4 --output-dir ~/subs --format srt
```

## Subcommands

| Command | Description |
|---|---|
| `subtitle <video>` | Transcribe and write subtitle file |
| `subtitle <video> --merge` | Transcribe + mux soft subtitles into a copy of the video |
| `subtitle <video> --burn` | Transcribe + burn hard subtitles into a copy of the video |
| `subtitle setup-whisper` | Build `whisper-cli` into user data dir (one-time) |
| `subtitle models --list` | List/check downloaded models |
| `subtitle batch --input-dir <dir>` | Batch-process a directory in parallel |
| `subtitle convert <in> [out]` | Convert existing subtitle files (`vtt`, `srt`, `csv`, `lrc`, `txt`) |
| `subtitle formats` | Show supported subtitle formats |

## Options

| Flag | Description |
|---|---|
| `--model`, `-m` | `tiny` / `base` / `small` / `medium` / `turbo` / `large-v3` / `large` (default: `base`) |
| `--format`, `-f` | `vtt` / `srt` / `txt` / `json` / `lrc` / `csv` (default: `vtt`) |
| `--language`, `-l` | Spoken language code (`en`, `es`, `auto`, etc.) |
| `--translate`, `-tr` | Translate speech to English |
| `--max-len`, `-ml` | Maximum segment length in characters (e.g. `16` for short-form captions) |
| `--split-on-word`, `-sow` | Split segments on word boundaries rather than tokens |
| `--prompt` | Initial prompt to guide vocabulary, names, or formatting |
| `--merge` | Embed soft subtitles into a copy of the video |
| `--burn` | Burn hard subtitles into a copy of the video |
| `--output-dir`, `-o` | Output directory (default: current dir) |
| `--threads`, `-t` | `whisper.cpp` thread count |
| `--whisper-binary` | Override the auto-discovered `whisper-cli` path |
| `--models-dir` | Override the model cache directory |
| `--verbose`, `-v` | Verbose output |
| `--version`, `-V` | Show version |

## Python API

```python
from subtitle_generator.core import SubtitleGenerator, WhisperCppTranscriber
from subtitle_generator.models import ModelManager

generator = SubtitleGenerator(
    transcriber=WhisperCppTranscriber(),
    model_manager=ModelManager(),
)
result = generator.generate(
    input_path="video.mp4",
    model_name="base",
    output_format="srt",
)
print(result.output_path if result.success else result.error)
```

## Links

- Source: <https://github.com/innovatorved/subtitle>
- Issues: <https://github.com/innovatorved/subtitle/issues>

## License

MIT
