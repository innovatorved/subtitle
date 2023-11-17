#!/usr/bin/env python

import sys
import argparse
import logging

from app.core import add_subtitle_in_video

# Configure logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add subtitles to video.")
    parser.add_argument("filepath", type=str, help="The path to the video file.")
    parser.add_argument("--model", type=str, default="base", help="The model name.")
    args = parser.parse_args()

    if not args.filepath:
        print("Please provide a filename.")
        sys.exit(1)

    try:
        vtt_file_path, output_file = add_subtitle_in_video(args.filepath, args.model)
        logger.info(f"VTT file path: {vtt_file_path}, Output file path: {output_file}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
