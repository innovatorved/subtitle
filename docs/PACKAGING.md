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
| `ffmpeg-python` | Video/audio processing | `src/core/video_processor.py` |
| `tqdm` | Progress bars | `src/models/model_manager.py`, `src/utils/downloader.py` |
| `pyyaml` | Config loading | `src/config/config_loader.py` |
| `gdown` | Google Drive downloads | `src/utils/downloader.py` (lazy import) |

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

```bash
# 1. Install build tools
pip install build twine

# 2. Build distribution
python -m build

# 3. Upload to PyPI
twine upload dist/*
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Modern PEP 621 package config |
| `MANIFEST.in` | Controls source distribution contents |
| `setup.py` | Backward compatibility for older pip |
| `.gitignore` | Excludes `dist/`, `build/`, `*.egg-info/` |
