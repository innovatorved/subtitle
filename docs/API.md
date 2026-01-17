# API Reference

Programmatic API documentation for the Subtitle tool.

## Core Classes

### SubtitleGenerator

Main class for generating subtitles from video/audio files.

```python
from src.core import SubtitleGenerator, WhisperCppTranscriber
from src.models import ModelManager

transcriber = WhisperCppTranscriber(threads=4)
model_manager = ModelManager()
generator = SubtitleGenerator(transcriber, model_manager)

result = generator.generate(
    input_path="video.mp4",
    model_name="base",
    output_format="srt",
    output_dir="./output",
)

if result.success:
    print(f"Saved: {result.output_path}")
else:
    print(f"Error: {result.error}")
```

**Parameters:**
- `input_path`: Path to video/audio file or URL
- `model_name`: Whisper model (`tiny`, `base`, `small`, `medium`, `large`)
- `output_format`: Output format (`vtt`, `srt`, `txt`, `json`, `lrc`, `ass`, `ttml`)
- `output_dir`: Optional output directory
- `progress_callback`: Optional callback for progress updates

---

### AsyncProcessor

Concurrent video processing using asyncio.

```python
import asyncio
from src.core import AsyncProcessor

async def main():
    async with AsyncProcessor(max_workers=4) as processor:
        # Process single video
        result = await processor.process_single("video.mp4", model="base")
        
        # Process multiple videos concurrently
        summary = await processor.process_multiple(
            video_paths=["video1.mp4", "video2.mp4", "video3.mp4"],
            model="base",
            output_format="srt",
        )
        
        print(f"Processed: {summary.successful}/{summary.total_files}")

asyncio.run(main())
```

**Parameters:**
- `max_workers`: Number of parallel workers (default: 4)

**Methods:**
- `process_single(video_path, model, output_format, output_dir)` → `BatchFileResult`
- `process_multiple(video_paths, model, output_format, output_dir, progress_callback)` → `BatchSummary`
- `shutdown(wait=True)` → Clean up resources

---

### BatchProcessor

Sequential batch processing with resume capability.

```python
from src.core import BatchProcessor

processor = BatchProcessor(
    workers=4,
    model="base",
    output_format="vtt",
)

summary = processor.process_batch(
    input_dir="./videos",
    output_dir="./subtitles",
    resume=True,  # Resume from previous run
)

print(f"Successful: {summary.successful}")
print(f"Failed: {summary.failed}")
print(summary.generate_report())
```

---

### ModelManager

Manage Whisper model downloads and caching.

```python
from src.models import ModelManager

manager = ModelManager()

# List available models
models = manager.list_models()
for model in models:
    status = "✓" if model.downloaded else "○"
    print(f"{status} {model.name} ({model.size})")

# Download a model
manager.download_model("small")

# Get model path
path = manager.get_model_path("base")
```

---

## Data Classes

### BatchFileResult

Result of processing a single file.

```python
@dataclass
class BatchFileResult:
    file_path: str
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: str = ...
```

### BatchSummary

Summary of batch processing.

```python
@dataclass
class BatchSummary:
    total_files: int
    successful: int
    failed: int
    skipped: int
    total_duration_seconds: float
    results: list[BatchFileResult]
    
    def generate_report(self) -> str:
        """Generate markdown report."""
```

---

## Validators

### SubtitleValidator

Validate subtitle quality and timing.

```python
from src.utils.validators import SubtitleValidator

validator = SubtitleValidator()

# Validate SRT file
result = validator.validate_file("subtitles.srt")
if result.is_valid:
    print("Subtitles are valid!")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

---

## Formatters

Convert between subtitle formats.

```python
from src.utils.formatters import SubtitleFormatter

formatter = SubtitleFormatter()

# Convert SRT to VTT
formatter.convert("input.srt", "output.vtt")

# Supported formats: vtt, srt, ass, ttml, json, lrc, txt
```
