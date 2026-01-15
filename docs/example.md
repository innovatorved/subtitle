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

### Batch Processing

```bash
for video in *.mp4; do
    python subtitle.py "$video" --model small
done
```

### Processing with Custom Output

```python
from src.core import WhisperCppTranscriber, SubtitleGenerator

transcriber = WhisperCppTranscriber(threads=8)
generator = SubtitleGenerator(transcriber)

result = generator.generate(
    input_path="video.mp4",
    model_name="small",
    output_format="srt",
)

if result.success:
    print(f"Saved: {result.output_path}")
```

