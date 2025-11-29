import logging
import os
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

        base, ext = os.path.splitext(file)
        output_file = f"{base}_subtitled{ext}"
        process_id, output_audio_path, vtt_file_path = generate_vtt_file(
            file, model_names[model]
        )
        # Rename VTT file to match input file
        final_vtt_path = f"{base}.vtt"
        if os.path.exists(vtt_file_path):
            os.rename(vtt_file_path, final_vtt_path)
            vtt_file_path = final_vtt_path

        logger.info(
            f"Output audio path: {output_audio_path}, VTT file path: {vtt_file_path}"
        )
        print("file", file, vtt_file_path, output_file)
        merge_video_and_vtt(file, vtt_file_path, output_file)
        return [vtt_file_path, output_file]
    except Exception as e:
        logger.error(f"An error occurred: {e}")
