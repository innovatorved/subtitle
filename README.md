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

### FFmpeg
First, you need to install FFmpeg. Here's how you can do it:

```bash
# On Linux
sudo apt install ffmpeg
```

## Run
You can run the script from the command line using the following command:

```bash
python subtitle.py <filepath | video_url> [--model <modelname>]
```
Replace `<filepath | video_url>` with the path to your video file. The `--model` argument is optional. If not provided, it will use 'base' as the default model.

For example:
```bash
python subtitle.py /path/to/your/video.mp4 --model base
```
This will run the script on the video at `/path/to/your/video.mp4` using the `base` model.
Please replace `/path/to/your/video.mp4` with the actual path to your video file.


### Models
Here are the models you can use:
Note: Use the `.en` model only when the video is in English.

- tiny.en
- tiny
- tiny-q5_1
- tiny.en-q5_1
- base.en
- base
- base-q5_1
- base.en-q5_1
- small.en
- small.en-tdrz
- small
- small-q5_1
- small.en-q5_1
- medium
- medium.en
- medium-q5_0
- medium.en-q5_0
- large-v1
- large-v2
- large
- large-q5_0

### Advance
You can modify the behaviour by using these parameters `whisper` binary as follows:


```bash
./whisper [options] file0.wav file1.wav ...
```

### Options
Here are the options you can use with the `whisper` binary:
| Option | Default | Description |
|--------|---------|-------------|
| `-h, --help` | | Show help message and exit |
| `-t N, --threads N` | 4 | Number of threads to use during computation |
| `-p N, --processors N` | 1 | Number of processors to use during computation |
| `-ot N, --offset-t N` | 0 | Time offset in milliseconds |
| `-on N, --offset-n N` | 0 | Segment index offset |
| `-d N, --duration N` | 0 | Duration of audio to process in milliseconds |
| `-mc N, --max-context N` | -1 | Maximum number of text context tokens to store |
| `-ml N, --max-len N` | 0 | Maximum segment length in characters |
| `-sow, --split-on-word` | false | Split on word rather than on token |
| `-bo N, --best-of N` | 2 | Number of best candidates to keep |
| `-bs N, --beam-size N` | -1 | Beam size for beam search |
| `-wt N, --word-thold N` | 0.01 | Word timestamp probability threshold |
| `-et N, --entropy-thold N` | 2.40 | Entropy threshold for decoder fail |
| `-lpt N, --logprob-thold N` | -1.00 | Log probability threshold for decoder fail |
| `-debug, --debug-mode` | false | Enable debug mode (eg. dump log_mel) |
| `-tr, --translate` | false | Translate from source language to English |
| `-di, --diarize` | false | Stereo audio diarization |
| `-tdrz, --tinydiarize` | false | Enable tinydiarize (requires a tdrz model) |
| `-nf, --no-fallback` | false | Do not use temperature fallback while decoding |
| `-otxt, --output-txt` | true | Output result in a text file |
| `-ovtt, --output-vtt` | false | Output result in a vtt file |
| `-osrt, --output-srt` | false | Output result in a srt file |
| `-olrc, --output-lrc` | false | Output result in a lrc file |
| `-owts, --output-words` | false | Output script for generating karaoke video |
| `-fp, --font-path` | /System/Library/Fonts/Supplemental/Courier New Bold.ttf | Path to a monospace font for karaoke video |
| `-ocsv, --output-csv` | false | Output result in a CSV file |
| `-oj, --output-json` | false | Output result in a JSON file |
| `-ojf, --output-json-full` | false | Include more information in the JSON file |
| `-of FNAME, --output-file FNAME` | | Output file path (without file extension) |
| `-ps, --print-special` | false | Print special tokens |
| `-pc, --print-colors` | false | Print colors |
| `-pp, --print-progress` | false | Print progress |
| `-nt, --no-timestamps` | false | Do not print timestamps |
| `-l LANG, --language LANG` | en | Spoken language ('auto' for auto-detect) |
| `-dl, --detect-language` | false | Exit after automatically detecting language |
| `--prompt PROMPT` | | Initial prompt |
| `-m FNAME, --model FNAME` | models/ggml-base.en.bin | Model path |
| `-f FNAME, --file FNAME` | | Input WAV file path |
| `-oved D, --ov-e-device DNAME` | CPU | The OpenVINO device used for encode inference |
| `-ls, --log-score` | false | Log best decoder scores of tokens |
| `-ng, --no-gpu` | false | Disable GPU |


### Example for running Binary
Here's an example of how to use the whisper binary:

```bash
./whisper -m models/ggml-tiny.en.bin -f Rev.mp3 out.wav -nt --output-vtt

```

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
