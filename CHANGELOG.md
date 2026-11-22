# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [4.0.0] - 2026-11-22

### Added
- **Cross-Platform Prebuilt Binaries & GPU Auto-Detection:** `subtitle setup-whisper` now downloads SHA-256 verified prebuilt `whisper-cli` binaries from GitHub Releases (macOS arm64/x86_64 Metal, Linux x86_64/arm64, Windows x64) with automatic CMake source-build fallback (`--from-source`, `--gpu auto|metal|cuda|vulkan|cpu`) and Windows `vswhere.exe` MSVC detection.
- **`subtitle doctor`:** Full environment diagnostics for OS, CPU, GPU backends, `whisper-cli` capabilities (`-vi`, `--vad`, `-pp`, `-dtw`, `-tdrz`, `-ojf`), `ffmpeg`/`ffprobe` + hardware encoders, disk space, and optional extras.
- **Silero VAD & Live Progress Streaming:** Silero VAD (`ggml-silero-v5.1.2.bin`, auto-downloaded) is enabled by default (`--no-vad` to disable), cutting silence hallucinations and accelerating transcription 2–3×. `WhisperCppTranscriber` now streams live `-pp` stderr progress and handles clean `SIGINT`/timeout child termination.
- **Broadcast & Creator Post-Processing (`--preset`):** Built-in `netflix`, `netflix-kids`, `bbc`, `reels`, and `shorts` presets with CPL/CPS reflow, balanced linguistic line wrapping, and Whisper hallucination/repetition scrubbing (`--scrub`).
- **Styled `.ass` & Word-Highlighted Karaoke Captions:** Added `ASSFormatter` (`clean`, `box`, `karaoke`, `cinema` styles with `\kf` word-level karaoke tags), `TTMLFormatter`, and `JSONFormatter` (parsing `whisper.cpp -oj / -ojf` word timings).
- **Single-Pass Multi-Format Export:** `--format srt,vtt,ass,ttml,json` emits multiple formats in a single transcription run.
- **Full Subtitle Toolkit Subcommands:** `subtitle lint` (Netflix/BBC/Reels QC), `subtitle shift` (`+/- ms` sync), `subtitle translate` (offline Argos or OpenAI/Groq LLM preserving timestamps), `subtitle watch` (folder automation with file-size stability debounce), `subtitle config` (`~/.config/subtitle-generator/config.toml` + `.subtitle.toml`), and `--json` machine-readable output.
- **Pluggable Multi-Backend Architecture:** `--backend whisper.cpp|faster-whisper|openai|groq` via optional extras.
- **Speaker Diarization & Decoding Controls:** `--diarize` (`-di`), `--tinydiarize` (`-tdrz`), `--word-timestamps`, `--carry-initial-prompt`, `--beam-size`, `--best-of`, `--no-gpu`.
- **DevOps & Distribution:** `.github/workflows/ci.yml` (`ruff`, `mypy`, cross-OS matrix), `.github/workflows/build-binaries.yml`, `Dockerfile`, and `Formula/subtitle-generator.rb`.

### Changed
- **Ultra-Light Core Dependencies:** Removed unmaintained `ffmpeg-python` (replaced with direct `subprocess` FFmpeg/FFprobe runner with Windows-safe filter escaping, live `-progress pipe:1`, hardware H.264 encoder auto-detection, and optional `imageio-ffmpeg` fallback). Moved `gdown` to optional `[gdrive]` extra and added `[yt]` (`yt-dlp`), `[ffmpeg]`, `[faster-whisper]`, `[cloud]`, `[translate]`, and `[all]` extras.
- **ModelManager:** Replaced rigid global singleton with per-`models_dir` caching, streaming `urlopen(..., timeout=30)` downloads with HTTP Range resume, and SHA-256 verification.
- **BatchProcessor:** Smart CPU thread budgeting across parallel workers, `--recursive` discovery, default video + audio support, and `--merge` / `--burn` / `--preset` support in batch mode.
- **Auto CPU Threads:** `WhisperCppTranscriber` defaults to `min(8, os.cpu_count() or 4)` instead of hardcoded `4`.

## [3.2.1] - 2026-11-21

### Added
- Online documentation site at [subtitle.vedgupta.in](https://subtitle.vedgupta.in) built with Vite + Tailwind CSS v4 and auto-deployed via Cloudflare Pages.
- `--threads` / `-t` and `--processors` / `-p` options on `subtitle batch` and `BatchProcessor`.
- Automatic Google Drive URL detection in `download_file()` (routes `drive.google.com` links to `gdown`) and `output_dir` support.

### Fixed
- `VideoProcessor.burn_subtitles()` now preserves the original audio stream (`acodec="copy"`) when burning hardcoded subtitles instead of dropping audio, and escapes `[` / `]` in subtitle paths.
- `VideoProcessor` now captures FFmpeg stdout/stderr so errors surface clean stderr diagnostics.
- `WhisperCppTranscriber` now extracts 16 kHz mono WAV via FFmpeg for non-WAV audio formats (e.g. `.m4a`, `.aac`, `.wma`) when using stock `whisper-cli` binaries without `-vi`.
- `ModelManager` now serializes model downloads with a thread lock (preventing `.part` races in parallel batch jobs) and fixes `tqdm` progress bar overshoot.
- `VTTFormatter` and `SRTFormatter` now handle Windows CRLF (`\r\n`) line endings, UTF-8 BOM headers, `MM:SS.mmm` WebVTT timestamps, and integer-millisecond timestamp rounding.
- `TXTFormatter.format([])` now returns `""` instead of `"\n"`.
- Moved `logging.basicConfig()` out of module import time into CLI `main()` so library callers' logging is never modified.
- Made `--merge` and `--burn` mutually exclusive in the CLI, cleaned up temporary downloaded URL media automatically, and added `--help` support to `subtitle formats`.

### Changed
- Updated dependencies to latest versions (`tqdm>=4.70.1`, `gdown>=6.5.2`, `setuptools>=84.0`, `wheel>=0.48.0`, dev tools) and modernized PEP 639 SPDX license metadata in `pyproject.toml`.

## [3.2.0] - 2026-10-23

### Added
- `--max-len` (`-ml`) and `--split-on-word` (`-sow`) options across CLI (`subtitle` and `subtitle batch`), `WhisperCppTranscriber`, `SubtitleGenerator`, and `BatchProcessor` for short-form / word-boundary caption splitting.
- `--prompt` option across CLI and Python API to pass an initial prompt guiding domain vocabulary, names, and style.
- `subtitle convert <input> [output] [--format <fmt>]` CLI subcommand and `convert_subtitle_file()` Python API helper.
- Added `CSVFormatter`, `LRCFormatter`, and `TXTFormatter` to `SubtitleFormatterFactory` so subtitle files can be converted across `vtt`, `srt`, `csv`, `lrc`, and `txt`.
- Re-exported core classes (`SubtitleGenerator`, `WhisperCppTranscriber`, `VideoProcessor`, `BatchProcessor`, `ModelManager`, `convert_subtitle_format`, `convert_subtitle_file`) directly from top-level `subtitle_generator`.

## [3.1.0] - 2026-10-23

### Added
- Support for updated `whisper.cpp` (`1.9.5-dev` / `ggml 0.27.0`) from `innovatorved/whisper.cpp` (`develop`).
- Expanded Whisper model catalog: `large-v3`, `large-v3-q5_0`, `large-v3-turbo` (plus `turbo` alias), `large-v3-turbo-q5_0`, `large-v3-turbo-q8_0`, `large-v2-q5_0`, `large-v2-q8_0`, and `-q8_0` quantized variants for `tiny`, `base`, `small`, and `medium`.
- `--language` / `-l` and `--translate` / `-tr` flags in CLI (`subtitle` and `subtitle batch`), `WhisperCppTranscriber`, `SubtitleGenerator`, and `BatchProcessor`.
- `--burn` flag in CLI to burn (hardcode) subtitles into a copy of the video (`<name>_burned.<ext>`).
- `--version` / `-V` CLI flag and `csv` (`-ocsv`) output format support.
- Automatic `-vi` capability detection in `WhisperCppTranscriber` with transparent 16 kHz mono WAV extraction fallback via FFmpeg when using stock/system `whisper-cli` binaries.

### Changed
- Updated all build, runtime, and development package dependencies to latest versions and added Python 3.13 to the CI matrix.
- `BatchProcessor` now executes concurrently using `ThreadPoolExecutor` when `workers > 1` with thread-safe state persistence.
- `setup_whisper` automatically invalidates stale CMake `build/` directories when the `whisper.cpp` git `HEAD` changes during update.
- `VideoProcessor.merge_subtitles` auto-selects the container-appropriate subtitle codec (`mov_text` for MP4/MOV/M4V, `srt` for MKV, `webvtt` for WebM).

### Fixed
- Fixed HuggingFace 404 on `--model large` and `--model large-q5_0` by mapping them to `ggml-large-v3.bin` and `ggml-large-v3-q5_0.bin`.
- Removed destructive `os.rename(filepath, sanitize_filename(filepath))` in CLI that renamed/moved user input files containing spaces.
- Made `ModelManager` model downloads atomic via `.part` temporary files and `os.replace`.
- Replaced unsafe `eval()` in `VideoProcessor.get_video_info` frame-rate parsing with a safe rational parser.
- Unified model list and `ValidationError` definitions across `ModelManager`, `validators`, and `exceptions`.

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
