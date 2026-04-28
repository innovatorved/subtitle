# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [3.0.5] - 2026-04-28

### Changed
- Trimmed docs, tests, and code to be minimal. Single CI workflow,
  shorter docstrings, removed dead code (`async_processor`,
  `config/`, the old `setup_whisper.sh`).

### Removed
- `setup_whisper.sh` — superseded by `subtitle setup-whisper` (same
  fork, same branch, works on Windows and after `pip install`).
- `.github/workflows/test.yml`, `.github/workflows/verify_whisper.yml`
  — `release.yml` already runs the cross-OS test matrix.
- `subtitle_generator.config` package and its tests (unused).
- `subtitle_generator.core.async_processor` (unused).
- `docs/PACKAGING.md`, `docs/example.md` (folded into README).

## [3.0.4] - 2026-04-28

### Changed
- Output now lands in the directory the command was run from, not next
  to the input video. Same applies to `--merge`.

### Added
- `--output-dir` / `-o` flag to override the default (CWD).
- `SubtitleGenerator.generate_and_rename(output_path=...)` for the
  Python API.

### Fixed
- `generate_and_rename` uses `shutil.move` so `/tmp` → `$HOME`
  cross-filesystem moves no longer raise `OSError: Cross-device link`.

## [3.0.3] - 2026-04-28

### Added
- `subtitle setup-whisper` subcommand. Clones, builds, and installs the
  project's compatible whisper.cpp fork (`innovatorved/whisper.cpp`,
  `develop`) into the per-OS user data dir. Flags: `--repo`, `--ref`,
  `--force`, `--no-pull`.
- `SUBTITLE_DATA_DIR` env var.

### Changed
- `find_whisper_binary` now prefers the `setup-whisper` binary over
  anything on PATH, bypassing Homebrew's incompatible `whisper-cpp 1.8.4`.

## [3.0.2] - 2026-04-28

### Fixed
- pip-installed CLI no longer fails with
  `./binary/whisper-cli: No such file or directory`. Binary is now
  resolved at runtime: `--whisper-binary`, `SUBTITLE_WHISPER_BINARY`,
  PATH, then the legacy checkout layout.
- Models cache no longer pollutes CWD; defaults to a per-OS user cache
  dir (override with `--models-dir` or `SUBTITLE_MODELS_DIR`).
- `subprocess` invocation switched from `shell=True` to argv list.
- `subtitle_generator.__version__` now matches the distribution version.

### Added
- `subtitle_generator.utils.paths` helpers, `--whisper-binary` /
  `--models-dir` flags on every command.

## [3.0.1] - 2026-04-28

### Changed
- Validate the GitHub Actions release pipeline end-to-end.

## [3.0.0] - 2026-04-28

### Breaking
- Top-level package renamed `src` → `subtitle_generator`.

### Added
- `.github/workflows/release.yml`: tag-triggered cross-OS CI + PyPI
  publish.

### Changed
- `pyproject.toml`: accurate description, removed personal handle from
  keywords, updated package + script paths for the new module name.

## How to release

```bash
# 1. Bump pyproject.toml + subtitle_generator/__init__.py to X.Y.Z
# 2. Push the commit and tag:
git commit -am "Release X.Y.Z"
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin master vX.Y.Z
```

`release.yml` runs the cross-OS test matrix, builds, smoke-installs the
wheel, and publishes to PyPI. Required secret: `TWINE_TOKEN`.
