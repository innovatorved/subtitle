# Package Distribution Guide

> Complete guide for installing, developing, and publishing the subtitle-generator package.

## Installation

### From PyPI (when published)
```bash
pip install subtitle-generator
```

### From Source (development)
```bash
git clone https://github.com/innovatorved/subtitle.git
cd subtitle
pip install -e ".[dev]"
```

## Dependencies

| Package | Purpose | Used In |
|---------|---------|---------|
| `ffmpeg-python` | Video/audio processing | `subtitle_generator/core/video_processor.py` |
| `tqdm` | Progress bars | `subtitle_generator/models/model_manager.py`, `subtitle_generator/utils/downloader.py` |
| `pyyaml` | Config loading | `subtitle_generator/config/config_loader.py` |
| `gdown` | Google Drive downloads | `subtitle_generator/utils/downloader.py` (lazy import) |

### Optional: Dev Dependencies
```bash
pip install subtitle-generator[dev]
# Includes: pytest, pytest-cov, black, isort, mypy, flake8, build, twine
```

## CLI Usage

```bash
subtitle video.mp4              # Generate VTT subtitles
subtitle video.mp4 --format srt # Generate SRT format
subtitle video.mp4 --merge      # Embed subtitles in video
subtitle models --list          # List available models
subtitle batch --input-dir /dir # Batch process videos
```

## Publishing to PyPI

The recommended path is the automated GitHub Actions release pipeline (see
[CHANGELOG.md](../CHANGELOG.md) for the full flow):

```bash
# 1. Bump `version` in pyproject.toml.
# 2. Commit and push, then push a matching tag:
git commit -am "Bump version to X.Y.Z"
git push origin master
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin vX.Y.Z
# GitHub Actions runs cross-OS tests, builds, and publishes automatically.
```

Manual publishing (only if the workflow is unavailable):

```bash
pip install build twine
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD='pypi-...' twine upload dist/*
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Modern PEP 621 package config |
| `MANIFEST.in` | Controls source distribution contents |
| `setup.py` | Backward compatibility for older pip |
| `.gitignore` | Excludes `dist/`, `build/`, `*.egg-info/` |
