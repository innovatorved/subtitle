# Subtitle
Open-source subtitle generation for seamless content translation.

Key Features:

- Open-source: Freely available for use, modification, and distribution.
- Self-hosted: Run the tool on your own servers for enhanced control and privacy.
- AI-powered: Leverage advanced machine learning for accurate and natural-sounding subtitles.
- Multilingual support: Generate subtitles for videos in a wide range of languages.
- Easy integration: Seamlessly integrates into your existing workflow.

> I made this project for fun, but I think it could also be useful for other people.

## Installation

### 1. Prerequisites
Ensure you have the following installed:
- `git`
- `make`
- `cmake`
- `ffmpeg` (Required for video processing)
- `conda` (Anaconda or Miniconda)

### 2. Setup Whisper.cpp
We use `whisper.cpp` for high-performance inference. Run the setup script to clone, compile, and configure it automatically:

```bash
./setup_whisper.sh
```

This script will:
- Clone the `whisper.cpp` repository.
- Detect your platform (macOS/Linux) and configure the build (Metal/CUDA support).
- Compile the `whisper-cli` binary.
- Install the binary to `./binary/whisper-cli`.
- Download the default `base` model to `./models/`.

### 3. Setup Conda Environment
We use Conda to manage dependencies and the environment.

1. **Create the environment:**
   ```bash
   conda env create -f environment.yml
   ```

2. **Activate the environment:**
   ```bash
   conda activate subtitle
   ```

3. **Verify installation:**
   ```bash
   python --version
   ```

## Usage

Run the subtitle generation script:

```bash
python subtitle.py <path_to_video_file> [--model <model_name>]
```

### Examples

**Basic usage (uses 'base' model by default):**
```bash
python subtitle.py example/story.mp4
```

**Specify a model:**
```bash
python subtitle.py example/story.mp4 --model base
```

**Using a URL (downloads and processes):**
```bash
python subtitle.py https://example.com/video.mp4
```

The script will generate a `.vtt` subtitle file in the `data/` directory and merge it with the video (if supported container) or output the path.

### Models
The following models are supported (will be downloaded automatically if not present):
- tiny, tiny.en
- base, base.en
- small, small.en
- medium, medium.en
- large-v1, large-v2, large-v3

Note: Use `.en` models for English-only content for better accuracy.

## License

[MIT](https://choosealicense.com/licenses/mit/)


## Reference & Credits

- [https://github.com/openai/whisper](https://github.com/openai/whisper)
- [https://openai.com/blog/whisper/](https://openai.com/blog/whisper/)
- [https://github.com/ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- [https://github.com/innovatorved/whisper.api](https://github.com/innovatorved/whisper.api)

  
## Authors

- [Ved Gupta](https://www.github.com/innovatorved)

  
## 🚀 About Me
Just try to being a Developer!

  
## Support

For support, email vedgupta@protonmail.com
