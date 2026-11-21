---
title: Python API
description: Use subtitle-generator as a clean, modular Python library for transcription, batch processing, video operations, and format conversion.
---

## Quick Example

Importing `subtitle_generator` never mutates your application's logging configuration. All core classes are re-exported from the top-level package.

```python
from subtitle_generator import (
    SubtitleGenerator,
    WhisperCppTranscriber,
    ModelManager,
)

generator = SubtitleGenerator(
    transcriber=WhisperCppTranscriber(threads=4),
    model_manager=ModelManager(),
)

result = generator.generate(
    input_path="video.mp4",
    model_name="turbo",
    output_format="srt",
    output_dir="./output",
    language="en",
)

if result.success:
    print("Subtitles saved to:", result.output_path)
else:
    print("Error:", result.error)
```

---

## Route Output to an Exact Path

Use `generate_and_rename` to write transient `whisper-cli` files into a temp directory and atomically move the final subtitle to an exact destination path:

```python
from subtitle_generator import SubtitleGenerator, WhisperCppTranscriber
from subtitle_generator.utils.paths import default_output_dir

generator = SubtitleGenerator(WhisperCppTranscriber())

final_path, ok = generator.generate_and_rename(
    input_path="interview.mp4",
    model_name="base",
    output_format="srt",
    output_dir=default_output_dir(),
    output_path="/Users/me/subs/interview.srt",
    language="es",
    translate=True,
    max_len=42,
    split_on_word=True,
    prompt="Whisper.cpp, FFmpeg",
)
```

---

## Parallel Batch Processing

```python
from subtitle_generator import BatchProcessor

processor = BatchProcessor(
    workers=4,
    threads=2,
    model="small",
    output_format="srt",
    language="en",
)

summary = processor.process_batch(
    input_dir="./videos",
    output_dir="./subs",
    resume=True,
    progress_callback=lambda path, cur, total, status: print(f"[{cur}/{total}] {path}: {status}"),
)

print(summary.generate_report())
```

---

## Video Operations (FFmpeg)

```python
from subtitle_generator import VideoProcessor

vp = VideoProcessor(overwrite_output=True)

# Soft-mux subtitles (auto-detects mov_text / srt / webvtt)
vp.merge_subtitles("video.mp4", "video.srt", "video_subtitled.mp4")

# Hard-burn subtitles (preserves original audio stream)
vp.burn_subtitles("video.mp4", "video.srt", "video_burned.mp4", font_size=24)

# Extract 16 kHz mono WAV audio
wav_path = vp.extract_audio("video.mp4", sample_rate=16000)

# Inspect video metadata
info = vp.get_video_info("video.mp4")
print(info["duration"], info["width"], info["height"], info["fps"])
```

---

## Format Conversion & Custom Formatters

```python
from subtitle_generator import convert_subtitle_file, convert_subtitle_format
from subtitle_generator.utils.formatters import SubtitleFormatterFactory

# Convert in-memory strings
srt_text = convert_subtitle_format(vtt_text, "vtt", "srt")

# Convert files on disk
out_path = convert_subtitle_file("captions.vtt", "captions.srt")

# Register your own custom formatter
# SubtitleFormatterFactory.register_formatter("ass", MyASSFormatter)
```

---

## Model Management & Setup

```python
from subtitle_generator import ModelManager
from subtitle_generator.utils.whisper_setup import setup_whisper

# Manage GGML models
mgr = ModelManager()
print("Available:", mgr.list_available_models())
print("Cached:", mgr.list_downloaded_models())
model_path = mgr.download_model("turbo")

# Build whisper-cli programmatically
setup_result = setup_whisper(force=False)
print("Binary:", setup_result.binary_path)
```

---

## Exception Hierarchy

All custom exceptions inherit from `SubtitleError`, so you can catch them individually or with a single base handler:

```python
from subtitle_generator.utils.exceptions import (
    SubtitleError,
    TranscriptionError,
    VideoProcessingError,
    ModelError,
    ValidationError,
    DownloadError,
    BatchProcessingError,
)
```
