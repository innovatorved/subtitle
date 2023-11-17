#!/bin/bash

# This script downloads Whisper model files that have already been converted to ggml format.
# This way you don't have to convert them yourself.

#src="https://ggml.ggerganov.com"
#pfx="ggml-model-whisper"

src="https://huggingface.co/ggerganov/whisper.cpp"
pfx="resolve/main/ggml"

# get the path of this script
function get_script_path() {
    if [ -x "$(command -v realpath)" ]; then
        echo "$(dirname "$(realpath "$0")")"
    else
        local ret="$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)"
        echo "$ret"
    fi
}

models_path="$(get_script_path)"

# Whisper models
models=( 
    "tiny.en"
    "tiny"
    "tiny-q5_1"
    "tiny.en-q5_1"
    "base.en"
    "base"
    "base-q5_1"
    "base.en-q5_1"
    "small.en"
    "small.en-tdrz"
    "small"
    "small-q5_1"
    "small.en-q5_1"
    "medium"
    "medium.en"
    "medium-q5_0"
    "medium.en-q5_0"
    "large-v1"
    "large-v2"
    "large"
    "large-q5_0"
)

# list available models
function list_models {
    printf "\n"
    printf "  Available models:"
    for model in "${models[@]}"; do
        printf " $model"
    done
    printf "\n\n"
}

if [ "$#" -ne 1 ]; then
    printf "Usage: $0 <model>\n"
    list_models

    exit 1
fi

model=$1

if [[ ! " ${models[@]} " =~ " ${model} " ]]; then
    printf "Invalid model: $model\n"
    list_models

    exit 1
fi

# check if model contains `tdrz` and update the src and pfx accordingly
if [[ $model == *"tdrz"* ]]; then
    src="https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"
    pfx="resolve/main/ggml"
fi

# download ggml model

printf "Downloading ggml model $model from '$src' ...\n"

cd "$models_path"

if [ -f "ggml-$model.bin" ]; then
    printf "Model $model already exists. Skipping download.\n"
    exit 0
fi

if [ -x "$(command -v wget)" ]; then
    wget --no-config --quiet --show-progress -O ggml-$model.bin $src/$pfx-$model.bin
elif [ -x "$(command -v curl)" ]; then
    curl -L --output ggml-$model.bin $src/$pfx-$model.bin
else
    printf "Either wget or curl is required to download models.\n"
    exit 1
fi


if [ $? -ne 0 ]; then
    printf "Failed to download ggml model $model \n"
    printf "Please try again later or download the original Whisper model files and convert them yourself.\n"
    exit 1
fi

printf "Done! Model '$model' saved in 'models/ggml-$model.bin'\n"
printf "You can now use it like this:\n\n"
printf "  $ ./main -m models/ggml-$model.bin -f samples/jfk.wav\n"
printf "\n"
