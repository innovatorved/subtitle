"""
Cross-platform filesystem path resolution for binaries and caches.

Centralises the logic for:
  * locating the `whisper-cli` binary at runtime (no hardcoded relative paths)
  * choosing a writable, OS-appropriate cache directory for downloaded models

Both are designed to work whether the package is installed via pip, run from a
git checkout, or invoked from an arbitrary CWD.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from typing import Optional

logger = logging.getLogger(__name__)


# Environment variables that let users override defaults without code changes.
ENV_WHISPER_BINARY = "SUBTITLE_WHISPER_BINARY"
ENV_MODELS_DIR = "SUBTITLE_MODELS_DIR"
ENV_DATA_DIR = "SUBTITLE_DATA_DIR"

# Names that whisper.cpp ships its CLI under across releases / package managers.
# Order matters: we prefer the canonical upstream name first.
_WHISPER_BINARY_NAMES = ("whisper-cli", "whisper-cpp", "main")


def _is_executable_file(path: str) -> bool:
    """Return True if `path` exists, is a regular file, and is executable."""
    try:
        return os.path.isfile(path) and os.access(path, os.X_OK)
    except OSError:
        return False


def _candidate_with_exe(path: str) -> str:
    """On Windows, append `.exe` if the path doesn't already end with it.

    Returns the original path on non-Windows or if `.exe` is already present.
    """
    if sys.platform != "win32":
        return path
    if path.lower().endswith(".exe"):
        return path
    return path + ".exe"


def find_whisper_binary(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the path to the whisper.cpp CLI binary.

    Lookup order (first hit wins):
        1. ``explicit`` argument (e.g. from a CLI ``--whisper-binary`` flag).
        2. The ``SUBTITLE_WHISPER_BINARY`` environment variable.
        3. The binary installed by ``subtitle setup-whisper`` into the
           per-OS user data dir. This is checked before ``PATH`` so that
           the project's known-compatible fork (which still supports the
           ``-vi`` video-input flag and direct ``.mp4`` ingestion) is
           preferred over any incompatible system-wide install (e.g.
           Homebrew's ``whisper-cpp 1.8.4`` dropped ``-vi``).
        4. ``shutil.which`` against known binary names. Picks up system
           installs and anything the user added to ``PATH``.
        5. A legacy ``./binary/whisper-cli`` (or ``.exe`` on Windows)
           relative to the current working directory. Preserves
           backwards compatibility with the project's checkout layout.

    Returns the absolute path to an executable, or ``None`` if no candidate
    is found. Callers are expected to surface a helpful error in the latter
    case (see :func:`whisper_binary_install_hint`).
    """

    def _normalise(p: str) -> Optional[str]:
        # Expand ~ and turn into an absolute path so downstream argv calls
        # are unambiguous regardless of subsequent CWD changes.
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
        logger.debug("Explicit whisper binary path %r not usable", explicit)

    env_value = os.environ.get(ENV_WHISPER_BINARY)
    if env_value:
        resolved = _normalise(env_value)
        if resolved:
            return resolved
        logger.warning(
            "%s=%r is set but does not point to an executable file",
            ENV_WHISPER_BINARY,
            env_value,
        )

    bundled = installed_whisper_binary()
    if bundled:
        return bundled

    for name in _WHISPER_BINARY_NAMES:
        # `shutil.which` already handles PATHEXT (.exe) on Windows.
        on_path = shutil.which(name)
        if on_path and _is_executable_file(on_path):
            return os.path.abspath(on_path)

    legacy = os.path.join(os.getcwd(), "binary", "whisper-cli")
    resolved = _normalise(legacy)
    if resolved:
        return resolved

    return None


def whisper_binary_install_hint() -> str:
    """Return a user-facing string explaining how to obtain whisper-cli.

    The first option is always ``subtitle setup-whisper``: that command
    builds the project's own compatible fork (which still supports the
    ``-vi`` video-input flag) into the user data dir, with no manual
    PATH or env-var fiddling required. The remaining options are
    fallbacks for users who prefer a system install or already have a
    compatible binary somewhere.
    """
    primary = (
        "\n  - Recommended: run `subtitle setup-whisper` once. This builds"
        "\n      whisper.cpp from source into your user data dir and is"
        "\n      auto-discovered on every subsequent invocation. Requires"
        "\n      git, cmake, and a C++ compiler on your machine."
    )
    common = (
        "\n  - Or set the SUBTITLE_WHISPER_BINARY environment variable to the"
        "\n      absolute path of an existing whisper-cli binary."
        "\n  - Or pass --whisper-binary /absolute/path/to/whisper-cli on the CLI."
    )
    if sys.platform == "darwin":
        os_hint = (
            "\n  - macOS toolchain: install Xcode CLI tools and cmake:"
            "\n      xcode-select --install && brew install cmake ffmpeg"
        )
    elif sys.platform.startswith("linux"):
        os_hint = (
            "\n  - Linux toolchain: install build essentials:"
            "\n      sudo apt-get install -y build-essential cmake git ffmpeg"
        )
    elif sys.platform == "win32":
        os_hint = (
            "\n  - Windows toolchain: install Visual Studio Build Tools, CMake,"
            "\n      and Git for Windows; or download a prebuilt whisper-cli.exe"
            "\n      release and add its folder to PATH."
        )
    else:
        os_hint = (
            "\n  - Toolchain: install git, cmake, make, and a C++ compiler."
        )
    return (
        "Could not find the `whisper-cli` binary on this system."
        + primary
        + os_hint
        + common
    )


def default_models_dir() -> str:
    """Return a writable, OS-appropriate directory for cached Whisper models.

    Resolution order:
        1. ``SUBTITLE_MODELS_DIR`` environment variable, if set.
        2. Per-OS user cache location:
            * macOS:   ``~/Library/Caches/subtitle-generator/models``
            * Windows: ``%LOCALAPPDATA%/subtitle-generator/Cache/models``
            * Linux:   ``$XDG_CACHE_HOME/subtitle-generator/models`` falling
                       back to ``~/.cache/subtitle-generator/models``.

    The directory is **not** created here; callers create it lazily so that
    instantiating a ``ModelManager`` has no filesystem side effects on
    import.
    """
    env_dir = os.environ.get(ENV_MODELS_DIR)
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))

    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches/subtitle-generator")
    elif sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser(
            "~/AppData/Local"
        )
        base = os.path.join(local_app, "subtitle-generator", "Cache")
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        if xdg:
            base = os.path.join(xdg, "subtitle-generator")
        else:
            base = os.path.expanduser("~/.cache/subtitle-generator")

    return os.path.join(base, "models")


def default_output_dir() -> str:
    """Return a writable directory for transient transcription output.

    Whisper.cpp writes its raw output here under a UUID-prefixed name; the
    final subtitle file is then renamed next to the user's input video.
    Using a temp-style path avoids polluting the user's CWD with a ``data/``
    folder on every invocation.
    """
    import tempfile

    return os.path.join(tempfile.gettempdir(), "subtitle-generator")


def default_data_dir() -> str:
    """Return a per-OS user *data* directory (distinct from cache).

    Used by ``subtitle setup-whisper`` to host the cloned whisper.cpp
    source tree and its compiled ``whisper-cli`` binary so they survive
    cache cleanup and are reused across invocations.

    Resolution order:
        1. ``SUBTITLE_DATA_DIR`` environment variable, if set.
        2. Per-OS default:
           * macOS:   ``~/Library/Application Support/subtitle-generator``
           * Windows: ``%LOCALAPPDATA%/subtitle-generator``
           * Linux:   ``$XDG_DATA_HOME/subtitle-generator`` (fallback to
                      ``~/.local/share/subtitle-generator``).
    """
    env_dir = os.environ.get(ENV_DATA_DIR)
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))

    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/subtitle-generator"
        )
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser(
            "~/AppData/Local"
        )
        return os.path.join(local_app, "subtitle-generator")
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return os.path.join(xdg, "subtitle-generator")
    return os.path.expanduser("~/.local/share/subtitle-generator")


def installed_whisper_binary() -> Optional[str]:
    """Return the path to the whisper-cli binary installed by
    ``subtitle setup-whisper`` into the user data dir, or ``None`` if not
    present. Used as a high-priority lookup in :func:`find_whisper_binary`.
    """
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
    """Return the absolute path where ``subtitle setup-whisper`` should
    install the compiled whisper-cli binary. Always returns the same path
    for the current OS; the file may or may not exist yet.
    """
    bin_dir = os.path.join(default_data_dir(), "bin")
    name = "whisper-cli.exe" if sys.platform == "win32" else "whisper-cli"
    return os.path.join(bin_dir, name)
