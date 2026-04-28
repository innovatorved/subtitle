# Python API

## Generate subtitles

```python
from subtitle_generator.core import SubtitleGenerator, WhisperCppTranscriber
from subtitle_generator.models import ModelManager

gen = SubtitleGenerator(
    transcriber=WhisperCppTranscriber(threads=4),
    model_manager=ModelManager(),
)

result = gen.generate(
    input_path="video.mp4",
    model_name="base",
    output_format="srt",
    output_dir="./output",
)
print(result.output_path if result.success else result.error)
```

## Route output to a specific path

```python
final_path, ok = gen.generate_and_rename(
    input_path="video.mp4",
    model_name="base",
    output_format="srt",
    output_dir="/tmp/sg",                # transient whisper output
    output_path="/Users/me/subs/video.srt",
)
```

## Batch (sequential, with resume)

```python
from subtitle_generator.core import BatchProcessor

summary = BatchProcessor(
    workers=4,
    model="base",
    output_format="srt",
).process_batch(
    input_dir="./videos",
    output_dir="./subs",
    resume=True,
)
print(summary.generate_report())
```

## Models

```python
from subtitle_generator.models import ModelManager

mgr = ModelManager()
print(mgr.list_available_models())
print(mgr.list_downloaded_models())
mgr.download_model("small")
```

## Build whisper-cli programmatically

```python
from subtitle_generator.utils.whisper_setup import setup_whisper

result = setup_whisper(force=False)
print(result.binary_path)
```

## Format conversion

```python
from subtitle_generator.utils.formatters import convert_subtitle_format

vtt = convert_subtitle_format(srt_text, "srt", "vtt")
```
