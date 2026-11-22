<p align="center">
  <img src="docs/public/logo.png" alt="Subtitle CLI" width="160" />
</p>

# Subtitle Generator

[![PyPI](https://badge.fury.io/py/subtitle-generator.svg)](https://pypi.org/project/subtitle-generator/)
[![Docs](https://img.shields.io/badge/docs-subtitle.vedgupta.in-F97316)](https://subtitle.vedgupta.in)
[![Version](https://img.shields.io/badge/version-v4.1.0-18181b)](https://github.com/innovatorved/subtitle/releases/tag/v4.1.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Industry-standard, cross-platform AI subtitle generation, styling, QC, and embedding toolkit.**  
Runs locally on macOS (Apple Silicon Metal), Linux (CPU / CUDA / Vulkan), Windows, and Docker — with optional `faster-whisper` and OpenAI/Groq cloud backends.

## Highlights (v4.0.0)

- **Zero-Friction Cross-Platform Setup:** `subtitle setup-whisper` downloads a SHA-256 verified prebuilt `whisper-cli` binary in ~2 seconds (with automatic CMake + GPU source-build fallback). Run `subtitle doctor` anytime to verify OS, GPU, `ffmpeg`, and models.
- **Silero VAD + Live Progress:** Voice Activity Detection (`--vad`, on by default) eliminates silence hallucinations and speeds up transcription 2–3×, with real-time percentage progress streaming.
- **Broadcast & Creator Standards:** Built-in Netflix, BBC, and Reels/Shorts presets (`--preset netflix|bbc|reels`) enforcing CPL, CPS, balanced 2-line wrapping, and hallucination scrubbing — plus `subtitle lint` for automated QC.
- **Styled `.ass` & Word-Highlighted Karaoke Captions:** Burn clean, box, cinema, or TikTok/Reels karaoke captions (`--burn --style karaoke --preset reels`) with hardware H.264 encoder auto-detection (`videotoolbox` / `nvenc`).
- **One-Pass Multi-Format Export:** Emit `srt`, `vtt`, `ass`, `ttml`, `json`, `csv`, `lrc`, and `txt` in a single run (`--format srt,vtt,ass`).
- **Complete Subtitle Toolkit:** `doctor`, `batch` (recursive + audio + smart thread budgeting), `watch`, `convert`, `lint`, `shift`, `translate`, `config`, and `--json` output.
- **Ultra-Light Core:** Only `tqdm` + Python stdlib in core; install only the extras you need (`[ffmpeg]`, `[yt]`, `[gdrive]`, `[faster-whisper]`, `[cloud]`, `[translate]`, `[all]`).

## Install

```bash
pip install subtitle-generator
subtitle video.mp4              # auto-installs prebuilt whisper-cli + model on first run!
```

No compiler setup or extra setup command required — on first run, `subtitle` automatically downloads the SHA-256 verified prebuilt `whisper-cli` binary for your OS/CPU (`macOS`, `Linux`, `Windows`) in ~2 seconds. *(Use `subtitle setup-whisper --from-source --gpu cuda` only if you want a custom local compile.)*

Optional extras:

```bash
pip install 'subtitle-generator[yt]'              # YouTube / TikTok / Vimeo URLs via yt-dlp
pip install 'subtitle-generator[ffmpeg]'          # Bundled static ffmpeg fallback
pip install 'subtitle-generator[faster-whisper]'  # CTranslate2 NVIDIA GPU backend
pip install 'subtitle-generator[cloud]'           # OpenAI / Groq Whisper API + LLM translation
pip install 'subtitle-generator[translate]'       # Offline local subtitle translation (Argos)
pip install 'subtitle-generator[all]'             # Everything
```

## Quick Usage

```bash
# Generate VTT (default, with Silero VAD + auto threads)
subtitle video.mp4

# Broadcast-compliant multi-format export in ONE pass
subtitle video.mp4 --format srt,vtt,ass --preset netflix

# Viral word-highlighted TikTok / Reels / Shorts burned captions
subtitle reel.mp4 --burn --style karaoke --preset reels

# Embed selectable soft subtitles into a copy of the video
subtitle video.mp4 --merge --format srt

# Transcribe directly from YouTube (with [yt] extra)
subtitle "https://youtu.be/dQw4w9WgXcQ" --model turbo --format srt

# Switch backends seamlessly
subtitle video.mp4 --backend faster-whisper --model large-v3-turbo
subtitle video.mp4 --backend groq --format srt

# Everyday subtitle toolkit
subtitle lint video.srt --standard netflix
subtitle shift video.srt --offset +500 -o synced.srt
subtitle translate video.srt --to es
subtitle convert video.vtt video.ass --style box
subtitle batch -i ./videos -o ./subs --recursive --preset netflix
subtitle watch ./incoming -o ./subs --model turbo
subtitle config --init
```

## Subcommands

| Command | What it does |
|---|---|
| `subtitle <media-or-url>` | Transcribe, reflow, style, merge, or burn subtitles |
| `subtitle setup-whisper` | Install prebuilt `whisper-cli` (or compile from source with Metal/CUDA/Vulkan) |
| `subtitle doctor` | Diagnose OS, GPU, `whisper-cli`, `ffmpeg`, models, and extras |
| `subtitle models --list` | List / download Whisper models |
| `subtitle batch -i <dir>` | Parallel batch processing across video & audio (supports `--recursive`, `--resume`, `--merge`, `--burn`) |
| `subtitle watch <dir>` | Watch a folder and auto-subtitle new media files |
| `subtitle convert <in> [out]` | Convert between `vtt`, `srt`, `ass`, `ttml`, `json`, `csv`, `lrc`, `txt` |
| `subtitle lint <file>` | Validate CPL, CPS, durations, and overlaps (`netflix`, `bbc`, `reels`) |
| `subtitle shift <file> --offset <ms>` | Shift subtitle timestamps (`+500` / `-250` ms) |
| `subtitle translate <file> --to <lang>` | Translate an existing subtitle file preserving exact timestamps |
| `subtitle config --init` | Create `~/.config/subtitle-generator/config.toml` |
| `subtitle formats` | List all supported subtitle formats |

## Docker

```bash
docker build -t subtitle-generator .
docker run --rm -v "$PWD:/work" -v subtitle-models:/data/models subtitle-generator video.mp4 --format srt --preset netflix
```

## Python API

```python
from subtitle_generator import (
    SubtitleGenerator,
    WhisperCppTranscriber,
    ModelManager,
    lint_subtitle_file,
    shift_subtitle_file,
)

generator = SubtitleGenerator(
    transcriber=WhisperCppTranscriber(),
    model_manager=ModelManager(),
)
result = generator.generate(
    input_path="video.mp4",
    model_name="turbo",
    output_formats=["srt", "vtt", "ass"],
    preset="netflix",
    style="clean",
)
print(result.output_paths if result.success else result.error)
```

## Documentation & License

Live docs at **[subtitle.vedgupta.in](https://subtitle.vedgupta.in)**.  
MIT License — see [LICENSE](LICENSE).
