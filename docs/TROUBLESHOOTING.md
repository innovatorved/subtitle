# Troubleshooting

## "Could not find the whisper-cli binary"

Run the one-time setup:

```bash
subtitle setup-whisper
```

Needs `git`, `cmake`, a C++ compiler, and `ffmpeg`:

```bash
# macOS
xcode-select --install && brew install cmake ffmpeg
# Linux
sudo apt-get install -y build-essential cmake git ffmpeg
# Windows
# Install Git, CMake, VS Build Tools, ffmpeg.
```

To override the auto-discovered binary:

```bash
export SUBTITLE_WHISPER_BINARY=/path/to/whisper-cli
# or
subtitle video.mp4 --whisper-binary /path/to/whisper-cli
```

> Homebrew's `whisper-cpp` 1.8.4 dropped the `-vi` flag and rejects
> `.mp4` directly, so it cannot be used as a drop-in. `subtitle
> setup-whisper` builds a compatible fork instead.

## Transcription succeeds but no output file

Make sure `ffmpeg` is installed (whisper.cpp uses it to read video).
Then re-run with `--verbose` and check the temp dir:

```bash
subtitle video.mp4 --verbose
ls "$(python -c 'import tempfile,os; print(os.path.join(tempfile.gettempdir(), "subtitle-generator"))')"
```

## Slow processing

- Use a smaller model: `--model tiny`
- Increase threads: `--threads 8`
- For English-only content, use the `.en` variants (e.g. `base.en`)

## Out of memory

Use a smaller model or split the video:

```bash
ffmpeg -i large_video.mp4 -t 00:30:00 -c copy part1.mp4
```

## Model download fails

Try downloading directly:

```bash
subtitle models --download tiny
```

Or fetch manually from
<https://huggingface.co/ggerganov/whisper.cpp/tree/main>.

## Where things live (per OS)

| | macOS | Linux | Windows |
|---|---|---|---|
| Models cache | `~/Library/Caches/subtitle-generator/models` | `${XDG_CACHE_HOME:-~/.cache}/subtitle-generator/models` | `%LOCALAPPDATA%\subtitle-generator\Cache\models` |
| `setup-whisper` source + binary | `~/Library/Application Support/subtitle-generator` | `${XDG_DATA_HOME:-~/.local/share}/subtitle-generator` | `%LOCALAPPDATA%\subtitle-generator` |

Override via `SUBTITLE_MODELS_DIR` and `SUBTITLE_DATA_DIR`.

## Still stuck?

Open an issue at
<https://github.com/innovatorved/subtitle/issues> with your OS, Python
version, and full error message.
