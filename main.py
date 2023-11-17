from app.models import download_model, model_names
from app.utils.checks import check_models_exist
from app.utils import generate_vtt_file

if __name__ == "__main__":
    model = "base"
    if not check_models_exist(model):
        download_model(model)

    output_audio_path, vtt_file_path = generate_vtt_file("Rev.mp3", model_names[model])
    print(output_audio_path, vtt_file_path)
