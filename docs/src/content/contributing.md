---
title: Contributing
description: Local development setup, running the test suite, building distributions, and contributing to Subtitle CLI.
---

## Development Setup

```bash
git clone https://github.com/innovatorved/subtitle.git
cd subtitle

# Install package and dev dependencies in editable mode
pip install -e ".[dev]"

# One-time build of whisper-cli (optional for unit tests, required for live transcription)
subtitle setup-whisper
```

---

## Running Tests

The test suite uses `pytest` and runs in under a second with no network or binary required:

```bash
pytest -v
pytest --cov=subtitle_generator tests/unit/
```

---

## Building the Package

Verify sdist and wheel builds cleanly with `build` and `twine`:

```bash
python -m build
python -m twine check dist/*
```

---

## Running the Docs Locally

The documentation site lives in `docs/` and is built with Vite and Tailwind CSS v4:

```bash
cd docs
bun install
bun run dev
```

Build the static site for production:

```bash
cd docs
bun run build
```

---

## Project Layout

```
subtitle/
├── subtitle_generator/
│   ├── cli/          # Argument parsers, ConsoleProgressObserver, CLI runner
│   ├── core/         # Transcriber, SubtitleGenerator, VideoProcessor, BatchProcessor
│   ├── models/       # Thread-safe ModelManager singleton & HF downloader
│   └── utils/        # Formatters, validators, downloader, paths, whisper_setup
├── tests/unit/       # Fast unit tests
├── docs/             # Static documentation site (Vite + Tailwind CSS v4)
└── pyproject.toml    # PEP 621 package metadata & entry points
```
