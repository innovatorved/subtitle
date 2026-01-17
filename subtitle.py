#!/usr/bin/env python
"""
Subtitle Generator - Add subtitles to videos using Whisper.

This is the main entry point for the subtitle generator CLI.
It supports both the new modular architecture (src/) and provides
backward compatibility with the legacy app/ module.

Usage:
    python subtitle.py video.mp4                 # Generate VTT subtitles
    python subtitle.py video.mp4 --merge         # Generate and embed subtitles
    python subtitle.py video.mp4 --model small   # Use different model
    python subtitle.py models --list             # List available models
    
For more options:
    python subtitle.py --help
"""

import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def main():
    """Main entry point."""
    try:
        # Use new modular CLI
        from src.cli import main as cli_main
        return cli_main()
    except ImportError as e:
        # Fallback to legacy implementation if new modules not available
        print(f"Warning: Could not import new modules ({e}), using legacy implementation.")
        return _legacy_main()


def _legacy_main():
    """Legacy main function for backward compatibility."""
    import argparse
    import logging
    
    from app.core import add_subtitle_in_video
    from app.utils import download_file, is_url
    
    # Configure logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Add subtitles to video.")
    parser.add_argument(
        "filepath", type=str, help="The path to the video file or its URL."
    )
    parser.add_argument("--model", type=str, default="base", help="The model name.")
    args = parser.parse_args()

    if not args.filepath:
        print("Please provide a filename.")
        return 1

    try:
        filepath = args.filepath
        if is_url(filepath):
            filepath = download_file(filepath)

        # Replace spaces with underscore
        if " " in filepath:
            filepath = filepath.replace(" ", "_")

        vtt_file_path, output_file = add_subtitle_in_video(filepath, args.model)
        logger.info(f"VTT file path: {vtt_file_path}, Output file path: {output_file}")
        print(f"Output filepath: {output_file}")
        return 0
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
