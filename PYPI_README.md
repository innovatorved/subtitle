# Subtitle Generator

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Docs](https://img.shields.io/badge/docs-subtitle.vedgupta.in-F97316)](https://subtitle.vedgupta.in)
[![Version](https://img.shields.io/badge/version-v4.1.1-18181b)](https://github.com/innovatorved/subtitle/releases/tag/v4.1.1)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Fast, offline AI subtitle generation for any video or audio file. Works out of the box on **macOS, Linux, and Windows**.

**Full Documentation:** **[https://subtitle.vedgupta.in](https://subtitle.vedgupta.in)**

## Install & Run

```bash
pip install subtitle-generator
subtitle video.mp4
```

No compiler or manual setup needed. On first run, `subtitle` automatically downloads the verified prebuilt `whisper-cli` binary, Silero VAD, and Whisper model for your OS.

## Common Examples

```bash
# Generate SRT subtitles (with Netflix readability formatting)
subtitle video.mp4 --format srt --preset netflix

# Embed soft subtitles into a copy of the video
subtitle video.mp4 --merge --format srt

# Burn word-highlighted Karaoke captions (TikTok / Reels / Shorts)
subtitle reel.mp4 --burn --style karaoke --preset reels

# Batch process a folder of videos
subtitle batch -i ./videos -o ./subs

# Check your environment & GPU acceleration
subtitle doctor
```

## Links

- **Documentation:** [https://subtitle.vedgupta.in](https://subtitle.vedgupta.in)
- **CLI Reference:** [https://subtitle.vedgupta.in/docs/cli-reference](https://subtitle.vedgupta.in/docs/cli-reference)
- **Source Code:** [https://github.com/innovatorved/subtitle](https://github.com/innovatorved/subtitle)
- **Issues:** [https://github.com/innovatorved/subtitle/issues](https://github.com/innovatorved/subtitle/issues)
