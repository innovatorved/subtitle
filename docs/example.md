# Usage Examples

## CLI Examples

### Basic Processing

```bash
# Generate VTT subtitles
python subtitle.py video.mp4

# Generate SRT format
python subtitle.py video.mp4 --format srt

# Embed subtitles into video
python subtitle.py video.mp4 --merge

# Use a specific model
python subtitle.py video.mp4 --model small
```

### Processing a Local Video

```bash
python subtitle.py ~/Videos/interview.mp4 --model base --merge
```

Output:
```
[PREP] Preparing 100%
[TRANS] Transcribing 100%
[MERGE] Merging 100%

[DONE] Success!
   Output: interview_subtitled.mp4
```

### Batch Processing (CLI)

```bash
# Process all videos in a directory
python subtitle.py batch ./videos --output ./subtitles --model base

# Resume interrupted batch
python subtitle.py batch ./videos --resume
```

### From URL

```bash
python subtitle.py "https://example.com/video.mp4" --format srt
```

---

## Python API Examples

### Basic Usage

```python
from src.core import WhisperCppTranscriber, SubtitleGenerator
from src.models import ModelManager

transcriber = WhisperCppTranscriber(threads=8)
model_manager = ModelManager()
generator = SubtitleGenerator(transcriber, model_manager)

result = generator.generate(
    input_path="video.mp4",
    model_name="small",
    output_format="srt",
)

if result.success:
    print(f"Saved: {result.output_path}")
```

### Async Processing (Multiple Videos)

```python
import asyncio
from src.core import AsyncProcessor

async def process_videos():
    videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
    
    async with AsyncProcessor(max_workers=4) as processor:
        summary = await processor.process_multiple(
            video_paths=videos,
            model="base",
            output_format="vtt",
        )
        
        print(f"Processed {summary.successful}/{summary.total_files} videos")
        for result in summary.results:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.file_path}")

asyncio.run(process_videos())
```

### Batch Processing with Progress

```python
from src.core import BatchProcessor

def on_progress(file_path, current, total, status):
    print(f"[{current}/{total}] {file_path}: {status}")

processor = BatchProcessor(model="base", output_format="srt")
summary = processor.process_batch(
    input_dir="./videos",
    output_dir="./subtitles",
    resume=True,
    progress_callback=on_progress,
)

print(summary.generate_report())
```

### Error Handling

```python
from src.core import SubtitleGenerator, WhisperCppTranscriber
from src.models import ModelManager
from src.utils.exceptions import (
    SubtitleError,
    ModelNotFoundError,
    TranscriptionError,
)

try:
    transcriber = WhisperCppTranscriber()
    model_manager = ModelManager()
    generator = SubtitleGenerator(transcriber, model_manager)
    
    result = generator.generate(
        input_path="video.mp4",
        model_name="base",
    )
    
    if not result.success:
        print(f"Failed: {result.error}")
        
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
except TranscriptionError as e:
    print(f"Transcription failed: {e}")
except SubtitleError as e:
    print(f"Error: {e}")
```

### Custom Output Directory

```python
result = generator.generate(
    input_path="input/video.mp4",
    model_name="base",
    output_format="vtt",
    output_dir="./custom_output",
)
```

---

## Format Conversion

### Convert Between Formats

```python
from src.utils.formatters import SubtitleFormatter

formatter = SubtitleFormatter()

# SRT to VTT
formatter.convert("subtitles.srt", "subtitles.vtt")

# VTT to ASS (with styling)
formatter.convert("subtitles.vtt", "subtitles.ass")
```

### Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| VTT | `.vtt` | WebVTT (web standard) |
| SRT | `.srt` | SubRip (most common) |
| ASS | `.ass` | Advanced SubStation Alpha |
| TTML | `.ttml` | Timed Text Markup Language |
| JSON | `.json` | Structured data |
| LRC | `.lrc` | Lyrics format |
| TXT | `.txt` | Plain text |
