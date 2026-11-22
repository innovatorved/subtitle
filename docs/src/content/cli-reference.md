---
title: CLI Reference
description: Complete command-line reference for subtitle v4.0.0 — transcribe, doctor, lint, shift, translate, watch, batch, convert, config, and setup-whisper.
---

## Commands Overview

| Command | Description |
|---------|-------------|
| `subtitle <media-or-url>` | Transcribe, reflow, style, merge, or burn subtitles |
| `subtitle doctor` | Diagnose OS, GPU, `whisper-cli`, `ffmpeg`, models, and extras |
| `subtitle setup-whisper` | Download prebuilt `whisper-cli` (or compile from source with Metal/CUDA/Vulkan) |
| `subtitle lint <file>` | Validate subtitle timing & readability (`netflix`, `bbc`, `reels`) |
| `subtitle shift <file> --offset <ms>` | Shift subtitle timestamps (`+500` / `-250` ms) |
| `subtitle translate <file> --to <lang>` | Translate an existing subtitle file preserving exact timestamps |
| `subtitle batch -i <dir>` | Parallel batch processing across video & audio (`--recursive`, `--resume`, `--merge`, `--burn`) |
| `subtitle watch <dir>` | Watch a folder and auto-subtitle newly added media files |
| `subtitle convert <in> [out]` | Convert between `vtt`, `srt`, `ass`, `ttml`, `json`, `csv`, `lrc`, `txt` |
| `subtitle config --init` | Create/inspect `~/.config/subtitle-generator/config.toml` |
| `subtitle models --list` | List and pre-download GGML models |
| `subtitle formats` | Display supported subtitle output formats |

---

## Transcribe (`subtitle <media>`)

```bash
subtitle video.mp4 [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--model MODEL` | `-m` | `base` | Whisper model (`tiny`, `base`, `small`, `medium`, `turbo`, `large-v3`, quantized) |
| `--format FMTS` | `-f` | `vtt` | Comma-separated format(s) in one pass: `vtt`, `srt`, `ass`, `ttml`, `json`, `csv`, `lrc`, `txt` |
| `--backend NAME` | | `whisper.cpp` | Engine: `whisper.cpp`, `faster-whisper`, `openai`, `groq` |
| `--preset NAME` | | `None` | Broadcast/creator reflow preset: `netflix`, `netflix-kids`, `bbc`, `reels`, `shorts` |
| `--vad` / `--no-vad` | | `--vad` | Enable/disable Silero VAD (eliminates silence hallucinations, 2–3× faster) |
| `--style STYLE` | | `clean` | ASS & burn style: `clean`, `box`, `karaoke`, `cinema` |
| `--font NAME` | | auto | Font family for `.ass` and `--burn` captions |
| `--font-size N` | | preset | Font size override for `.ass` and `--burn` |
| `--position POS` | | `bottom` | Vertical placement: `bottom`, `center`, `top` |
| `--language CODE` | `-l` | `None` | Spoken language (`en`, `es`, `hi`, `ja`, `auto`) |
| `--translate` | `-tr` | `False` | Translate spoken audio to English |
| `--diarize` | | `False` | Stereo channel speaker diarization (`-di`) |
| `--tinydiarize` | `-tdrz` | `False` | Inline speaker-turn diarization (`small.en-tdrz`) |
| `--word-timestamps` | | `False` | Preserve word-level timestamps in JSON/ASS |
| `--scrub` | | `False` | Scrub Whisper repetition & `[BLANK_AUDIO]` artifacts |
| `--prompt TEXT` | | `None` | Domain vocabulary / proper nouns prompt (`--carry-initial-prompt` for long videos) |
| `--merge` / `--burn` | | `False` | Soft-mux (`--merge`) or hardcode (`--burn`) subtitles into video copy |
| `--json` | | `False` | Machine-readable JSON output for scripts & pipelines |
| `--threads N` | `-t` | auto | CPU threads (defaults to `min(8, os.cpu_count())`) |
| `--no-gpu` | | `False` | Force CPU execution |
| `--output-dir DIR` | `-o` | CWD | Directory for output files |

---

## Quality Control (`subtitle lint`) & Timing (`subtitle shift`)

```bash
# Validate against Netflix 42 CPL / 20 CPS / 2-line rules (exit code 1 on errors)
subtitle lint episode.srt --standard netflix
subtitle lint episode.srt --standard bbc --json

# Fix out-of-sync subtitles by +500ms or -250ms without re-transcribing
subtitle shift episode.srt --offset 500 -o synced.srt
subtitle shift episode.srt --offset -250
```

---

## Translate (`subtitle translate`) & Watch (`subtitle watch`)

```bash
# Translate an existing subtitle file into Spanish (auto picks OpenAI/Groq or offline Argos)
subtitle translate video.srt --to es
subtitle translate video.srt --to fr --provider argos -o video.fr.srt

# Auto-subtitle new files dropped into ./incoming
subtitle watch ./incoming -o ./subs --model turbo --format srt --preset netflix --recursive
```

---

## Setup Whisper (`subtitle setup-whisper`)

```bash
subtitle setup-whisper                    # Fast prebuilt binary download (~2s)
subtitle setup-whisper --from-source      # Compile locally with auto GPU detection
subtitle setup-whisper --from-source --gpu cuda
```
