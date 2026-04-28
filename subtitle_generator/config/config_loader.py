"""
Configuration loader with YAML support.

Loads configuration from default.yaml and optionally overrides
with user-specific configuration.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from .settings import Settings

logger = logging.getLogger(__name__)

# Global settings instance
_settings: Optional[Settings] = None

# Default config locations
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default.yaml"
USER_CONFIG_PATH = Path.home() / ".subtitle" / "config.yaml"


def load_config(
    config_path: Optional[str] = None,
    user_config_path: Optional[str] = None,
) -> Settings:
    """
    Load configuration from YAML files.
    
    Loads the default configuration and optionally overrides with
    user-specific configuration.
    
    Args:
        config_path: Optional path to default config (uses built-in if None)
        user_config_path: Optional path to user config
        
    Returns:
        Settings instance with loaded configuration
    """
    global _settings
    
    # Start with defaults
    config_data = {}
    
    # Load default config
    default_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if default_path.exists():
        try:
            with open(default_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
            logger.debug(f"Loaded default config from: {default_path}")
        except Exception as e:
            logger.warning(f"Failed to load default config: {e}")
    
    # Load and merge user config
    user_path = Path(user_config_path) if user_config_path else USER_CONFIG_PATH
    if user_path.exists():
        try:
            with open(user_path, "r") as f:
                user_data = yaml.safe_load(f) or {}
            config_data = _deep_merge(config_data, user_data)
            logger.debug(f"Loaded user config from: {user_path}")
        except Exception as e:
            logger.warning(f"Failed to load user config: {e}")
    
    # Create settings from merged config
    _settings = Settings.from_dict(config_data)
    
    return _settings


def get_config() -> Settings:
    """
    Get the current configuration.
    
    Loads default configuration if not already loaded.
    
    Returns:
        Current Settings instance
    """
    global _settings
    
    if _settings is None:
        _settings = load_config()
    
    return _settings


def reset_config():
    """Reset configuration to force reload on next access."""
    global _settings
    _settings = None


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge two dictionaries.
    
    Values from override take precedence over base.
    Nested dictionaries are merged recursively.
    
    Args:
        base: Base dictionary
        override: Override dictionary
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def save_user_config(settings: Settings, path: Optional[str] = None):
    """
    Save settings to user config file.
    
    Args:
        settings: Settings to save
        path: Optional custom path (uses default user path if None)
    """
    config_path = Path(path) if path else USER_CONFIG_PATH
    
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        yaml.dump(settings.to_dict(), f, default_flow_style=False)
    
    logger.info(f"Saved user config to: {config_path}")
