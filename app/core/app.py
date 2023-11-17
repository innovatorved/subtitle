import logging
from app.models import download_model, model_names
from app.utils.checks import check_models_exist
from app.utils import generate_vtt_file, merge_video_and_vtt

# Configure logging
logger = logging.getLogger(__name__)


def process_video(file, model="base"):
    """
    add_subtitle_in_video
    @param file: video file path
    @param model: model name

    @return: [vtt_file_path , output_file]
    """
    try:
        if not check_models_exist(model):
            download_model(model)

        output_file = f"data/{file.split('.')[0]}_subtitled.{file.split('.')[1]}"
        process_id, output_audio_path, vtt_file_path = generate_vtt_file(
            file, model_names[model]
        )
        logger.info(
            f"Output audio path: {output_audio_path}, VTT file path: {vtt_file_path}"
        )
        merge_video_and_vtt(file, vtt_file_path, output_file)
        return [vtt_file_path, output_file]
    except Exception as e:
        logger.error(f"An error occurred: {e}")
