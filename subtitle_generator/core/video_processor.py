"""
Video processor module for FFmpeg operations.

Handles video-related operations like audio extraction, subtitle merging,
and format conversion using FFmpeg.
"""

import logging
import os
from typing import Optional

import ffmpeg

from ..utils.file_handler import file_exists

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Handles video processing operations using FFmpeg.
    
    Provides methods for merging subtitles, extracting audio,
    and other video manipulation tasks.
    """
    
    def __init__(self, overwrite_output: bool = True):
        """
        Initialize video processor.
        
        Args:
            overwrite_output: Whether to overwrite existing output files
        """
        self.overwrite_output = overwrite_output
    
    def merge_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        subtitle_codec: str = "mov_text",
    ) -> bool:
        """
        Merge subtitle file with video.
        
        Args:
            video_path: Path to input video file
            subtitle_path: Path to subtitle file (VTT, SRT, etc.)
            output_path: Path for output video with embedded subtitles
            subtitle_codec: Subtitle codec to use (mov_text, srt, ass, etc.)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If input files don't exist
        """
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not file_exists(subtitle_path):
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
        
        try:
            logger.info(f"Merging subtitles: {video_path} + {subtitle_path}")
            
            video = ffmpeg.input(video_path)
            subtitles = ffmpeg.input(subtitle_path)
            
            merged = ffmpeg.output(
                video,
                subtitles,
                output_path,
                vcodec="copy",
                acodec="copy",
                scodec=subtitle_codec,
            )
            
            ffmpeg.run(merged, overwrite_output=self.overwrite_output)
            
            logger.info(f"Successfully created: {output_path}")
            return True
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to merge subtitles: {e}")
            return False
    
    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        font_size: int = 24,
    ) -> bool:
        """
        Burn (hardcode) subtitles into video.
        
        This permanently embeds subtitles into the video stream.
        
        Args:
            video_path: Path to input video file
            subtitle_path: Path to subtitle file
            output_path: Path for output video
            font_size: Font size for burned subtitles
            
        Returns:
            True if successful, False otherwise
        """
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not file_exists(subtitle_path):
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
        
        try:
            logger.info(f"Burning subtitles into video: {video_path}")
            
            # Escape the subtitle path for the filter
            escaped_path = subtitle_path.replace(":", "\\:").replace("'", "\\'")
            
            video = ffmpeg.input(video_path)
            
            output = (
                video
                .filter("subtitles", escaped_path, force_style=f"FontSize={font_size}")
                .output(output_path)
            )
            
            ffmpeg.run(output, overwrite_output=self.overwrite_output)
            
            logger.info(f"Successfully burned subtitles: {output_path}")
            return True
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to burn subtitles: {e}")
            return False
    
    def extract_audio(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        audio_format: str = "wav",
        sample_rate: int = 16000,
    ) -> str:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to input video file
            output_path: Optional custom output path
            audio_format: Output audio format (wav, mp3, etc.)
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Path to extracted audio file
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If extraction fails
        """
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            base, _ = os.path.splitext(video_path)
            output_path = f"{base}.{audio_format}"
        
        try:
            logger.info(f"Extracting audio from: {video_path}")
            
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    acodec="pcm_s16le" if audio_format == "wav" else None,
                    ar=sample_rate,
                    ac=1,  # Mono
                )
                .run(overwrite_output=self.overwrite_output)
            )
            
            logger.info(f"Audio extracted to: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error: {error_msg}")
            raise RuntimeError(f"Failed to extract audio: {error_msg}")
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video file information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information (duration, resolution, etc.)
        """
        if not file_exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"),
                None
            )
            audio_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "audio"),
                None
            )
            
            info = {
                "duration": float(probe["format"].get("duration", 0)),
                "size_bytes": int(probe["format"].get("size", 0)),
                "format": probe["format"].get("format_name", "unknown"),
            }
            
            if video_stream:
                info["width"] = video_stream.get("width")
                info["height"] = video_stream.get("height")
                info["video_codec"] = video_stream.get("codec_name")
                info["fps"] = eval(video_stream.get("r_frame_rate", "0/1"))
            
            if audio_stream:
                info["audio_codec"] = audio_stream.get("codec_name")
                info["sample_rate"] = int(audio_stream.get("sample_rate", 0))
            
            return info
            
        except ffmpeg.Error as e:
            logger.error(f"Failed to probe video: {e}")
            raise RuntimeError(f"Failed to get video info: {e}")
