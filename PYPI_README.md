# Subtitle Generator

Generate subtitles for video/audio files using whisper.cpp.

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

> Homebrew's `whisper-cpp` 1.8.4 dropped the `-vi` flag we use to ingest
> video directly, so `subtitle setup-whisper` is the recommended way to
> get a compatible binary.

## Usage

```bash
# VTT (default), output in current directory
subtitle video.mp4

# SRT
subtitle video.mp4 --format srt

# Generate SRT and embed it into the video
# Writes ./video.srt and ./video_subtitled.mp4
subtitle video.mp4 --merge --format srt

# Larger model
subtitle video.mp4 --model large

# Custom output directory
subtitle /path/to/video.mp4 --output-dir ~/subs --format srt
```

## Subcommands

| Command | Description |
|---|---|
| `subtitle <video>` | Transcribe and write subtitle file |
| `subtitle <video> --merge` | Transcribe + mux into a copy of the video |
| `subtitle setup-whisper` | Build whisper-cli into user data dir (one-time) |
| `subtitle models --list` | List/check downloaded models |
| `subtitle batch --input-dir <dir>` | Batch-process a directory |
| `subtitle formats` | Show supported subtitle formats |

## Options

| Flag | Description |
|---|---|
| `--model`, `-m` | tiny / base / small / medium / large (default: base) |
| `--format`, `-f` | vtt / srt / txt / json / lrc (default: vtt) |
| `--merge` | Embed subtitles into a copy of the video |
| `--output-dir`, `-o` | Output directory (default: current dir) |
| `--threads`, `-t` | Whisper.cpp thread count |
| `--whisper-binary` | Override the auto-discovered whisper-cli path |
| `--models-dir` | Override the model cache directory |
| `--verbose`, `-v` | Verbose output |

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
