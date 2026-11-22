---
title: Python API
description: Use subtitle-generator v4.0 as a modular Python library for multi-backend transcription, Netflix/BBC reflow & QC, Karaoke ASS styling, translation, and folder watching.
---

## Quick Example (Multi-Format + Preset + VAD)

All core classes and helpers are re-exported from top-level `subtitle_generator`. Importing the library never modifies your application's logging configuration.

```python
from subtitle_generator import (
    SubtitleGenerator,
    WhisperCppTranscriber,
    ModelManager,
)

generator = SubtitleGenerator(
    transcriber=WhisperCppTranscriber(vad=True),
    model_manager=ModelManager(),
)

result = generator.generate(
    input_path="video.mp4",
    model_name="turbo",
    output_formats=["srt", "vtt", "ass"],
    output_dir="./output",
    preset="netflix",
    style="karaoke",
)

if result.success:
    print("Generated files:", result.output_paths)
else:
    print("Error:", result.error)
```

---

## Pluggable Backends (`create_transcriber`)

Switch between local `whisper.cpp`, CTranslate2 `faster-whisper`, OpenAI, or Groq with one parameter:

```python
from subtitle_generator import create_transcriber, SubtitleGenerator

# Local CTranslate2 on NVIDIA GPU (`pip install subtitle-generator[faster-whisper]`)
t_fw = create_transcriber("faster-whisper")

# Cloud Groq Whisper (`pip install subtitle-generator[cloud]`, set GROQ_API_KEY)
t_groq = create_transcriber("groq")

generator = SubtitleGenerator(t_groq)
result = generator.generate("podcast.mp3", output_format="srt", preset="netflix")
```

---

## QC Linting, Timestamp Shifting & Translation

```python
from subtitle_generator import (
    lint_subtitle_file,
    shift_subtitle_file,
    translate_subtitle_file,
    run_diagnostics,
)

# Validate against Netflix / BBC / Reels rules
report = lint_subtitle_file("video.srt", standard="netflix")
print("Passed:", report.passed, "Issues:", len(report.issues))

# Shift timestamps by +500ms
shift_subtitle_file("video.srt", offset_ms=500, output_path="synced.srt")

# Translate subtitles to Spanish preserving exact cue timestamps
translate_subtitle_file("video.srt", target_lang="es", provider="auto")

# Programmatic environment check
diag = run_diagnostics()
print("Ready:", diag["healthy"], "GPU:", diag["gpu"]["backends"])
```

---

## Video Operations (Direct FFmpeg Subprocess)

```python
from subtitle_generator import VideoProcessor

vp = VideoProcessor(overwrite_output=True)

# Soft-mux subtitles (instant stream copy, auto container codec)
vp.merge_subtitles("video.mp4", "video.srt", "video_subtitled.mp4")

# Hard-burn styled Karaoke captions (auto hardware H.264 + audio preserved)
vp.burn_subtitles(
    "reel.mp4",
    "reel.ass",
    "reel_burned.mp4",
    style="karaoke",
    position="bottom",
)
```
