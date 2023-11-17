import logging
from app.core import add_subtitle_in_video

# Configure logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        model = "base"
        file = "story.mp4"
        vtt_file_path, output_file = add_subtitle_in_video(file, model)
        logger.info(f"VTT file path: {vtt_file_path}, Output file path: {output_file}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
