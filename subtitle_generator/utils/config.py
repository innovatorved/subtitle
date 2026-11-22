"""Persistent TOML configuration support for subtitle-generator.

Loads defaults from:
1. User config: ``~/.config/subtitle-generator/config.toml`` (or OS equivalent)
2. Project-local config: ``./.subtitle.toml`` (overrides user config)

CLI flags always take highest precedence over config values.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

from .paths import default_config_path

logger = logging.getLogger(__name__)

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.9/3.10 fallback
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

DEFAULT_CONFIG_TEMPLATE = """\
# subtitle-generator configuration file
# CLI flags always override values set here.

[defaults]
model = "base"
format = "vtt"
backend = "whisper.cpp"
vad = true
# language = "en"
# preset = "netflix"
# threads = 4
# models_dir = ""
# whisper_binary = ""

[burn]
style = "clean"
font = "Arial"
# font_size = 24
position = "bottom"
"""


def _read_toml_file(path: str) -> dict[str, Any]:
    if not path or not os.path.isfile(path) or tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Failed to parse config file %s: %s", path, e)
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(
    user_config_path: Optional[str] = None,
    local_config_path: Optional[str] = None,
) -> dict[str, Any]:
    """Load merged configuration dictionary from user and local TOML files."""
    user_path = user_config_path or default_config_path()
    local_path = local_config_path or os.path.join(os.getcwd(), ".subtitle.toml")

    cfg = _read_toml_file(user_path)
    local_cfg = _read_toml_file(local_path)
    return _deep_merge(cfg, local_cfg)


def get_config_default(
    config: dict[str, Any],
    key: str,
    fallback: Any = None,
    section: str = "defaults",
) -> Any:
    """Lookup a key inside a config section (falling back to top-level then default)."""
    sec = config.get(section)
    if isinstance(sec, dict) and key in sec:
        val = sec[key]
        if val != "":
            return val
    if key in config and config[key] != "":
        return config[key]
    return fallback


def write_default_config(path: Optional[str] = None, overwrite: bool = False) -> str:
    """Write a starter ``config.toml`` file and return its path."""
    target = path or default_config_path()
    if os.path.exists(target) and not overwrite:
        return target
    parent = os.path.dirname(os.path.abspath(target))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)
    return target
