"""Cross-platform paths for the whisper-cli binary and the model cache."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from typing import Optional

logger = logging.getLogger(__name__)

ENV_WHISPER_BINARY = "SUBTITLE_WHISPER_BINARY"
ENV_MODELS_DIR = "SUBTITLE_MODELS_DIR"
ENV_DATA_DIR = "SUBTITLE_DATA_DIR"

_WHISPER_BINARY_NAMES = ("whisper-cli", "whisper-cpp", "main")


def _is_executable_file(path: str) -> bool:
    try:
        return os.path.isfile(path) and os.access(path, os.X_OK)
    except OSError:
        return False


def _candidate_with_exe(path: str) -> str:
    if sys.platform != "win32" or path.lower().endswith(".exe"):
        return path
    return path + ".exe"


def find_whisper_binary(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the whisper-cli binary path.

    Order: explicit arg, SUBTITLE_WHISPER_BINARY env var,
    binary installed by ``subtitle setup-whisper`` (preferred over PATH so
    incompatible system installs are bypassed), PATH, legacy
    ``./binary/whisper-cli`` checkout layout.
    """

    def _normalise(p: str) -> Optional[str]:
        p = os.path.abspath(os.path.expanduser(p))
        if _is_executable_file(p):
            return p
        win_p = _candidate_with_exe(p)
        if win_p != p and _is_executable_file(win_p):
            return win_p
        return None

    if explicit:
        resolved = _normalise(explicit)
        if resolved:
            return resolved

    env_value = os.environ.get(ENV_WHISPER_BINARY)
    if env_value:
        resolved = _normalise(env_value)
        if resolved:
            return resolved
        logger.warning("%s=%r is not an executable file", ENV_WHISPER_BINARY, env_value)

    bundled = installed_whisper_binary()
    if bundled:
        return bundled

    for name in _WHISPER_BINARY_NAMES:
        on_path = shutil.which(name)
        if on_path and _is_executable_file(on_path):
            return os.path.abspath(on_path)

    legacy = _normalise(os.path.join(os.getcwd(), "binary", "whisper-cli"))
    if legacy:
        return legacy

    return None


def whisper_binary_install_hint() -> str:
    """User-facing instructions for getting a working whisper-cli."""
    primary = (
        "\n  - Recommended: run `subtitle setup-whisper` once. Builds"
        "\n      whisper.cpp from source into your user data dir; auto-discovered"
        "\n      afterwards. Requires git, cmake, and a C++ compiler."
    )
    if sys.platform == "darwin":
        os_hint = (
            "\n  - macOS toolchain:"
            "\n      xcode-select --install && brew install cmake ffmpeg"
        )
    elif sys.platform.startswith("linux"):
        os_hint = (
            "\n  - Linux toolchain:"
            "\n      sudo apt-get install -y build-essential cmake git ffmpeg"
        )
    elif sys.platform == "win32":
        os_hint = (
            "\n  - Windows: install Visual Studio Build Tools, CMake, and Git for Windows."
        )
    else:
        os_hint = "\n  - Toolchain: install git, cmake, make, and a C++ compiler."
    common = (
        "\n  - Or set SUBTITLE_WHISPER_BINARY to an absolute path,"
        "\n  - Or pass --whisper-binary /path/to/whisper-cli."
    )
    return "Could not find the `whisper-cli` binary." + primary + os_hint + common


def default_models_dir() -> str:
    """Per-OS user cache directory for downloaded ggml models."""
    env_dir = os.environ.get(ENV_MODELS_DIR)
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))

    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches/subtitle-generator")
    elif sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        base = os.path.join(local_app, "subtitle-generator", "Cache")
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = os.path.join(xdg, "subtitle-generator") if xdg else os.path.expanduser(
            "~/.cache/subtitle-generator"
        )

    return os.path.join(base, "models")


def default_output_dir() -> str:
    """Temp dir for transient whisper-cli output (UUID-named files)."""
    import tempfile

    return os.path.join(tempfile.gettempdir(), "subtitle-generator")


def default_data_dir() -> str:
    """Per-OS user data directory used by ``subtitle setup-whisper``."""
    env_dir = os.environ.get(ENV_DATA_DIR)
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))

    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/subtitle-generator")
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return os.path.join(local_app, "subtitle-generator")
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return os.path.join(xdg, "subtitle-generator")
    return os.path.expanduser("~/.local/share/subtitle-generator")


def installed_whisper_binary() -> Optional[str]:
    """Path to the whisper-cli installed by ``subtitle setup-whisper`` (or None)."""
    bin_dir = os.path.join(default_data_dir(), "bin")
    candidate = os.path.join(bin_dir, "whisper-cli")
    if _is_executable_file(candidate):
        return candidate
    if sys.platform == "win32":
        candidate_exe = candidate + ".exe"
        if _is_executable_file(candidate_exe):
            return candidate_exe
    return None


def installed_whisper_binary_target() -> str:
    """Where ``subtitle setup-whisper`` installs the binary."""
    bin_dir = os.path.join(default_data_dir(), "bin")
    name = "whisper-cli.exe" if sys.platform == "win32" else "whisper-cli"
    return os.path.join(bin_dir, name)
