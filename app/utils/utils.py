import os
import re
import urllib
import subprocess
import uuid
import logging
import wave
import gdown
import ffmpeg

from tqdm import tqdm

from app.models import model_names
from .checks import chack_file_exist
from .contant import NO_OF_THREADS, NO_OF_PROCESSORS


def transcribe_file(path: str = None, model="ggml-model-whisper-tiny.en-q5_1.bin"):
    """./binary/whisper -m models/ggml-tiny.en.bin -f Rev.mp3 out.wav -nt --output-text out1.txt"""
    try:
        if path is None:
            raise Exception("No path provided")
        rand = uuid.uuid4()
        outputFilePath: str = f"transcribe/{rand}.txt"
        output_audio_path: str = f"audio/{rand}.wav"
        command: str = f"./binary/whisper -m models/{model} -f {path} {output_audio_path} -nt --output-text {outputFilePath}"
        execute_command(command)
        f = open(outputFilePath, "r")
        data = f.read()
        f.close()
        return [data, output_audio_path]
    except Exception as exc:
        logging.error(exc)
        raise Exception(exc.__str__())


def generate_vtt_file(path: str = None, model="ggml-tiny.bin"):
    """./whisper -m models/ggml-tiny.en.bin -f Rev.mp3 out.wav -nt --output-vtt"""
    try:
        if path is None or not chack_file_exist(path):
            raise Exception("PATH Error!")
        rand = uuid.uuid4()
        output_audio_path: str = f"data/{rand}.wav"
        vtt_file_path: str = f"data/{rand}.wav.vtt"
        command: str = f"./binary/whisper -t {NO_OF_THREADS} -p {NO_OF_PROCESSORS} -m models/{model} -f {path} {output_audio_path} -nt --output-vtt"
        execute_command(command)
        return [rand, output_audio_path, vtt_file_path]
    except Exception as exc:
        logging.error(exc)
        raise Exception(exc.__str__())


def execute_command(command: str) -> str:
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode("utf-8").strip()
    except subprocess.CalledProcessError as exc:
        logging.error(exc.output.decode("utf-8").strip())
        raise Exception("Error while transcribing")


def save_audio_file(file=None):
    if file is None:
        return ""
    path = f"audio/{uuid.uuid4()}.mp3"
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def get_audio_duration(audio_file):
    """Gets the duration of the audio file in seconds.

    Args:
      audio_file: The path to the audio file.

    Returns:
      The duration of the audio file in seconds.
    """

    with wave.open(audio_file, "rb") as f:
        frames = f.getnframes()
        sample_rate = f.getframerate()
        duration = frames / sample_rate
        rounded_duration = int(round(duration, 0))

    return rounded_duration


def get_model_name(model: str = None):
    if model is None:
        model = "tiny.en.q5"

    if model in model_names.keys():
        return model_names[model]

    return model_names["tiny.en.q5"]


def download_from_drive(url, output):
    try:
        gdown.download(url, output, quiet=False)
        return True
    except:
        raise Exception("Error Occured in Downloading model from Gdrive")


def download_file(url, filepath=None):
    try:
        filename = str(uuid.uuid4()) + ".mp4"

        if filepath is None:
            filepath = filename

        opener = urllib.request.build_opener()
        opener.addheaders = [("User-agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        with tqdm(
            unit="B", unit_scale=True, unit_divisor=1024, miniters=1, desc=filename
        ) as progress_bar:
            urllib.request.urlretrieve(
                url,
                filepath,
                reporthook=lambda block_num, block_size, total_size: progress_bar.update(
                    block_size
                ),
            )

        print("File downloaded successfully!")
        return filepath
    except Exception as exc:
        raise Exception(f"An error occurred: {exc}")


def merge_video_and_vtt(video_path, vtt_path, output_path):
    try:
        if not chack_file_exist(video_path):
            raise Exception("Video File Not Found!")
        if not chack_file_exist(vtt_path):
            raise Exception("VTT File Not Found!")

            # Load the input files
        video = ffmpeg.input(video_path)
        subtitles = ffmpeg.input(vtt_path)

        merged = ffmpeg.output(
            video,
            subtitles,
            output_path,
            vcodec="copy",
            scodec="mov_text",
        )

        ffmpeg.run(merged, overwrite_output=True)

        return True
    except Exception as exc:
        raise Exception(f"An error occurred: {exc}")


def is_url(filepath: str):
    try:
        result = urllib.parse.urlparse(filepath)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
