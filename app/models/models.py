import os
import requests
from tqdm import tqdm
import urllib


models = [
    "tiny.en",
    "tiny",
    "tiny-q5_1",
    "tiny.en-q5_1",
    "base.en",
    "base",
    "base-q5_1",
    "base.en-q5_1",
    "small.en",
    "small.en-tdrz",
    "small",
    "small-q5_1",
    "small.en-q5_1",
    "medium",
    "medium.en",
    "medium-q5_0",
    "medium.en-q5_0",
    "large-v1",
    "large-v2",
    "large",
    "large-q5_0",
]

model_names = {model: f"ggml-{model}.bin" for model in models}


def download_model(model_name):
    if model_name not in models:
        print(f"Invalid model: {model_name}")
        print("Available models: ", ", ".join(models))
        return

    src = "https://huggingface.co/ggerganov/whisper.cpp"
    pfx = "resolve/main/ggml"

    if "tdrz" in model_name:
        src = "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"
        pfx = "resolve/main/ggml"

    model_path = os.path.join(os.getcwd(), "models", f"ggml-{model_name}.bin")

    if os.path.exists(model_path):
        print(f"Model {model_name} already exists. Skipping download.")
        return

    print(f"Downloading ggml model {model_name} from '{src}' ...")

    url = f"{src}/{pfx}-{model_name}.bin"
    # response = requests.get(url)

    # if response.status_code != 200:
    #     print(f"Failed to download ggml model {model_name}")
    #     print(
    #         "Please try again later or download the original Whisper model files and convert them yourself."
    #     )
    #     return

    # with open(model_path, "wb") as f:
    #     f.write(response.content)

    download_file(url, model_path)

    print(f"Done! Model '{model_name}' saved in '{model_path}'")


def download_file(url, filepath):
    try:
        filename = os.path.basename(url)

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
    except Exception as exc:
        raise Exception(f"An error occurred: {exc}")
