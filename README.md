# Subtitle Generator

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Generate subtitles for video/audio files using `whisper.cpp`.

## Install

```bash
pip install subtitle-generator
subtitle setup-whisper          # one-time: clones + builds whisper-cli
```

`subtitle setup-whisper` needs `git`, `cmake`, a C++ compiler, and `ffmpeg`
on your PATH. Install instructions per OS:

```bash
# macOS
xcode-select --install && brew install cmake ffmpeg

# Linux (Debian/Ubuntu)
sudo apt-get install -y build-essential cmake git ffmpeg

# Windows
# Install Git for Windows, CMake, Visual Studio Build Tools, and ffmpeg.
```

## Usage

```bash
# Generate VTT (default) into the current directory
subtitle video.mp4

# Generate SRT
subtitle video.mp4 --format srt

# Generate SRT and embed it into the video as soft subtitles
# Output: ./video_subtitled.mp4 in your current directory
subtitle video.mp4 --merge --format srt

# Burn (hardcode) subtitles directly into the video stream
# Output: ./video_burned.mp4
subtitle video.mp4 --burn --format srt

# Use large-v3-turbo (fast + accurate) or large (large-v3)
subtitle video.mp4 --model turbo
subtitle video.mp4 --model large-v3

# Specify spoken language or translate non-English speech to English
subtitle video.mp4 --language es --translate

# Short-form / TikTok / Reels captions (max 16 chars per cue, split on words)
subtitle video.mp4 --format srt --max-len 16 --split-on-word

# Guide domain vocabulary or proper nouns with an initial prompt
subtitle video.mp4 --prompt "Whisper.cpp, PyPI, FFmpeg"

# Convert an existing subtitle file between formats (vtt, srt, csv, lrc, txt)
subtitle convert video.vtt video.srt

# Route output somewhere specific
subtitle /path/to/video.mp4 --format srt --output-dir ~/subs
```

## Embed or Burn Subtitles (`--merge` / `--burn`)

- **`--merge`**: Muxes the generated subtitle file into a copy of the video as a selectable soft subtitle track (`<name>_subtitled.<ext>`). Automatically picks the container codec (`mov_text` for MP4/MOV/M4V, `srt` for MKV, `webvtt` for WebM).
- **`--burn`**: Hardcodes subtitles into the video stream (`<name>_burned.<ext>`).

The original video is **never** modified.

## Subcommands

| Command | What it does |
|---|---|
| `subtitle <video>` | Transcribe and write subtitles |
| `subtitle <video> --merge` | Transcribe + embed soft subtitles into a copy of the video |
| `subtitle <video> --burn` | Transcribe + burn hard subtitles into a copy of the video |
| `subtitle setup-whisper` | One-time: build `whisper-cli` into your user data dir |
| `subtitle models --list` | List models, mark which are downloaded |
| `subtitle models --download <name>` | Pre-download a model |
| `subtitle batch --input-dir <dir>` | Process every video in a directory in parallel |
| `subtitle convert <in> [out]` | Convert existing subtitles between `vtt`, `srt`, `csv`, `lrc`, and `txt` |
| `subtitle formats` | Show supported subtitle formats (`vtt`, `srt`, `txt`, `json`, `lrc`, `csv`) |

## Models

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` / `tiny.en` | ~75 MB | fastest | low |
| `base` / `base.en` | ~140 MB | fast | medium (default) |
| `small` / `small.en` | ~460 MB | medium | good |
| `medium` / `medium.en` | ~1.5 GB | slow | great |
| `turbo` (`large-v3-turbo`) | ~1.5 GB | fast | near-best |
| `large` (`large-v3`) | ~3 GB | slowest | best |

Quantized models (`-q5_0`, `-q5_1`, `-q8_0`) are also supported (e.g. `large-v3-turbo-q5_0`, `base-q8_0`). Run `subtitle models --list` to see the full catalog.

## Troubleshooting

If transcription fails with a "could not find whisper-cli" error, run:

```bash
subtitle setup-whisper
```

That builds the project's `whisper.cpp` fork (`innovatorved/whisper.cpp`, branch `develop`, with native `-vi` video input support) into `<user-data>/bin/` and is auto-discovered on every subsequent invocation. If you point `--whisper-binary` at a stock `whisper-cli` without `-vi`, `subtitle-generator` automatically falls back to extracting 16 kHz mono WAV audio via `ffmpeg`.

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
    language="en",
)
print(result.output_path if result.success else result.error)
```

## License

MIT — see [LICENSE](LICENSE).
