#!/usr/bin/env python
"""
Subtitle Generator - Add subtitles to videos using Whisper.

This is the main entry point for the subtitle generator CLI.

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
    from src.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
