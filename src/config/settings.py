"""
Settings dataclass for typed configuration.

Provides a typed interface for accessing configuration values
with sensible defaults.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WhisperSettings:
    """Whisper-related settings."""
    
    default_model: str = "base"
    threads: int = 4
    processors: int = 1
    binary_path: str = "./binary/whisper-cli"


@dataclass
class PathSettings:
    """Path-related settings."""
    
    models_dir: str = "./models"
    data_dir: str = "./data"
    output_dir: str = "./output"


@dataclass
class FormatSettings:
    """Format-related settings."""
    
    default: str = "vtt"
    supported: list[str] = field(default_factory=lambda: ["vtt", "srt", "txt", "json", "lrc"])


@dataclass
class VideoSettings:
    """Video processing settings."""
    
    video_codec: str = "copy"
    audio_codec: str = "copy"
    subtitle_codec: str = "mov_text"
    overwrite_output: bool = True


@dataclass
class LoggingSettings:
    """Logging settings."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"


@dataclass
class Settings:
    """
    Main settings container.
    
    Holds all configuration values with typed access and defaults.
    """
    
    whisper: WhisperSettings = field(default_factory=WhisperSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    formats: FormatSettings = field(default_factory=FormatSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """
        Create Settings from a dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Settings instance
        """
        whisper_data = data.get("whisper", {})
        paths_data = data.get("paths", {})
        formats_data = data.get("formats", {})
        video_data = data.get("video", {})
        logging_data = data.get("logging", {})
        
        return cls(
            whisper=WhisperSettings(
                default_model=whisper_data.get("default_model", "base"),
                threads=whisper_data.get("threads", 4),
                processors=whisper_data.get("processors", 1),
                binary_path=whisper_data.get("binary_path", "./binary/whisper-cli"),
            ),
            paths=PathSettings(
                models_dir=paths_data.get("models_dir", "./models"),
                data_dir=paths_data.get("data_dir", "./data"),
                output_dir=paths_data.get("output_dir", "./output"),
            ),
            formats=FormatSettings(
                default=formats_data.get("default", "vtt"),
                supported=formats_data.get("supported", ["vtt", "srt", "txt", "json", "lrc"]),
            ),
            video=VideoSettings(
                video_codec=video_data.get("video_codec", "copy"),
                audio_codec=video_data.get("audio_codec", "copy"),
                subtitle_codec=video_data.get("subtitle_codec", "mov_text"),
                overwrite_output=video_data.get("overwrite_output", True),
            ),
            logging=LoggingSettings(
                level=logging_data.get("level", "INFO"),
                format=logging_data.get("format", "%(asctime)s - %(levelname)s - %(message)s"),
            ),
        )
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "whisper": {
                "default_model": self.whisper.default_model,
                "threads": self.whisper.threads,
                "processors": self.whisper.processors,
                "binary_path": self.whisper.binary_path,
            },
            "paths": {
                "models_dir": self.paths.models_dir,
                "data_dir": self.paths.data_dir,
                "output_dir": self.paths.output_dir,
            },
            "formats": {
                "default": self.formats.default,
                "supported": self.formats.supported,
            },
            "video": {
                "video_codec": self.video.video_codec,
                "audio_codec": self.video.audio_codec,
                "subtitle_codec": self.video.subtitle_codec,
                "overwrite_output": self.video.overwrite_output,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
            },
        }
