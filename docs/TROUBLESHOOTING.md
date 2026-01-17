# Troubleshooting Guide

Common issues and solutions for the Subtitle tool.

## Installation Issues

### FFmpeg Not Found

**Error:** `FFmpeg not found` or `FileNotFoundError: ffmpeg`

**Solution:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### Whisper.cpp Build Fails

**Error:** Build errors during `./setup_whisper.sh`

**Solutions:**

1. Ensure build tools are installed:
   ```bash
   # macOS
   xcode-select --install

   # Ubuntu/Debian
   sudo apt-get install build-essential cmake git
   ```

2. Clean and retry:
   ```bash
   rm -rf whisper.cpp
   ./setup_whisper.sh
   ```

### Model Download Fails

**Error:** `Failed to download model` or timeout errors

**Solutions:**

1. Check internet connection
2. Try with a smaller model first:
   ```bash
   python subtitle.py models --download tiny
   ```
3. Manual download from [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main)

---

## Runtime Issues

### Out of Memory

**Error:** Process killed or memory errors with large files

**Solutions:**

1. Use a smaller model:
   ```bash
   python subtitle.py video.mp4 --model tiny
   ```

2. Close other applications

3. For very large files, consider splitting:
   ```bash
   ffmpeg -i large_video.mp4 -t 00:30:00 -c copy part1.mp4
   ```

### Slow Processing

**Solutions:**

1. Increase threads:
   ```bash
   python subtitle.py video.mp4 --threads 8
   ```

2. Use a smaller model (`tiny` or `base`)

3. For batch processing, use async processor:
   ```python
   from src.core import AsyncProcessor

   async with AsyncProcessor(max_workers=4) as processor:
       results = await processor.process_multiple(video_paths)
   ```

### Audio Extraction Fails

**Error:** `Failed to extract audio` or format errors

**Solutions:**

1. Check video file is valid:
   ```bash
   ffprobe video.mp4
   ```

2. Try re-encoding:
   ```bash
   ffmpeg -i input.mp4 -c:v copy -c:a aac output.mp4
   ```

---

## Platform-Specific Issues

### macOS

**Issue:** Apple Silicon compatibility

The tool automatically uses optimized binaries for M1/M2/M3 chips. If issues occur:
```bash
# Force rebuild
rm -rf whisper.cpp binary/
./setup_whisper.sh
```

### Windows

**Issue:** Path too long errors

Enable long paths in Windows:
1. Run `regedit`
2. Navigate to `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
3. Set `LongPathsEnabled` to `1`

### Linux

**Issue:** Missing shared libraries

```bash
sudo apt-get install libsndfile1 libportaudio2
```

---

## Getting Help

If your issue isn't listed:

1. Check [GitHub Issues](https://github.com/innovatorved/subtitle/issues)
2. Open a new issue with:
   - OS and Python version
   - Full error message
   - Steps to reproduce
3. Contact: vedgupta@protonmail.com
