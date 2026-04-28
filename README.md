# Subtitle Generator

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Generate subtitles for video/audio files using whisper.cpp.

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

# Generate SRT *and* embed it into the video as soft subtitles
# Output: ./video_subtitled.mp4 in your current directory
subtitle video.mp4 --merge --format srt

# Larger model for better accuracy
subtitle video.mp4 --model large

# Route output somewhere specific
subtitle /path/to/video.mp4 --format srt --output-dir ~/subs
```

## Embed SRT into a video (`--merge`)

`--merge` runs the subtitle generation, then uses `ffmpeg` to mux the
generated SRT/VTT into the video as a soft subtitle track. The result is
a new file `<input-basename>_subtitled.<ext>` in your current directory
(or `--output-dir`). The original video is **not** modified.

```bash
subtitle interview.mp4 --merge --format srt
# writes:
#   ./interview.srt
#   ./interview_subtitled.mp4
```

The subtitle track is selectable in any modern player (VLC, mpv, QuickTime).

## Subcommands

| Command | What it does |
|---|---|
| `subtitle <video>` | Transcribe and write subtitles |
| `subtitle <video> --merge` | Transcribe + embed into a copy of the video |
| `subtitle setup-whisper` | One-time: build whisper-cli into your user data dir |
| `subtitle models --list` | List models, mark which are downloaded |
| `subtitle models --download <name>` | Pre-download a model |
| `subtitle batch --input-dir <dir>` | Process every video in a directory |
| `subtitle formats` | Show supported subtitle formats |

## Models

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~75 MB | fastest | low |
| `base` | ~140 MB | fast | medium (default) |
| `small` | ~460 MB | medium | good |
| `medium` | ~1.5 GB | slow | great |
| `large` | ~3 GB | slowest | best |

Use the `.en` variants (e.g. `base.en`) for English-only content for a
modest speed-up.

## Troubleshooting

If transcription fails with a "could not find whisper-cli" error, run:

```bash
subtitle setup-whisper
```

That builds the project's known-compatible fork
(`innovatorved/whisper.cpp`, branch `develop`) into `<user-data>/bin/`
and is auto-discovered on every subsequent invocation. Homebrew's
`whisper-cpp` 1.8.4 dropped the flag we use to ingest video directly,
so it is **not** sufficient — `setup-whisper` is the recommended path.

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

## License

MIT — see [LICENSE](LICENSE).
