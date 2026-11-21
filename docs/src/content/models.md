---
title: Models
description: Complete catalog of supported GGML Whisper models, quantization tradeoffs, and offline model management.
---

## Recommended Models

Models are downloaded automatically from Hugging Face (`ggerganov/whisper.cpp`) the first time you request them, verified atomically via a `.part` file, and cached in your user cache directory.

| Model | Approx. Size | Speed | Accuracy | Best For |
|-------|-------------|-------|----------|----------|
| `tiny` / `tiny.en` | ~75 MB | Fastest | Low | Quick drafts, low-RAM machines |
| `base` / `base.en` | ~140 MB | Fast | Medium *(default)* | Everyday videos, fast turnarounds |
| `small` / `small.en` | ~460 MB | Medium | Good | Podcasts, talks, tutorials |
| `medium` / `medium.en` | ~1.5 GB | Slow | Great | Noisy audio, accents, multilingual |
| `turbo` (`large-v3-turbo`) | ~1.5 GB | Fast | Near-best | Best overall speed-to-accuracy ratio |
| `large` (`large-v3`) | ~3.0 GB | Slowest | Best | Highest accuracy, archival transcription |

<Aside type="tip">
For English-only videos, the `.en` variants (`tiny.en`, `base.en`, `small.en`, `medium.en`) are noticeably more accurate than their multilingual counterparts at the same size.
</Aside>

---

## Quantized & Specialized Variants

Quantized models (`-q5_0`, `-q5_1`, `-q8_0`) reduce disk size and memory usage by 30–60% with minimal quality loss — ideal for laptops and parallel batch workers.

| Family | Available Identifiers |
|--------|-----------------------|
| Tiny | `tiny`, `tiny.en`, `tiny-q5_1`, `tiny.en-q5_1`, `tiny-q8_0`, `tiny.en-q8_0` |
| Base | `base`, `base.en`, `base-q5_1`, `base.en-q5_1`, `base-q8_0`, `base.en-q8_0` |
| Small | `small`, `small.en`, `small.en-tdrz`, `small-q5_1`, `small.en-q5_1`, `small-q8_0`, `small.en-q8_0` |
| Medium | `medium`, `medium.en`, `medium-q5_0`, `medium.en-q5_0`, `medium-q8_0`, `medium.en-q8_0` |
| Large v1/v2 | `large-v1`, `large-v2`, `large-v2-q5_0`, `large-v2-q8_0` |
| Large v3 | `large-v3`, `large-v3-q5_0`, `large` *(alias)*, `large-q5_0` *(alias)* |
| Large v3 Turbo | `large-v3-turbo`, `large-v3-turbo-q5_0`, `large-v3-turbo-q8_0`, `turbo` *(alias)* |

---

## Managing Models

List all available models and see which ones are already cached locally:

```bash
subtitle models --list
```

Pre-download a model before going offline:

```bash
subtitle models --download large-v3-turbo-q5_0
```

Use a custom cache directory (per-command or via environment variable):

```bash
export SUBTITLE_MODELS_DIR=/mnt/fast-ssd/whisper-models
subtitle video.mp4 --model turbo
```
