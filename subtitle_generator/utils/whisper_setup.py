"""
Cross-platform builder for the project's bundled whisper.cpp fork.

Implements the ``subtitle setup-whisper`` workflow: clone (or update) the
project's whisper.cpp fork, build the ``whisper-cli`` binary with CMake,
and install it into the per-OS user data dir so subsequent
``subtitle ...`` invocations can auto-discover it without any flags or
environment variables.

The fork pin is intentional: upstream whisper.cpp 1.8.x dropped the
``-vi`` (video-input) flag and rejects ``.mp4`` directly, breaking this
project's "pass a video, get subtitles" UX. ``innovatorved/whisper.cpp``
preserves that flag.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

from .exceptions import SubtitleError
from .paths import (
    default_data_dir,
    installed_whisper_binary_target,
)

logger = logging.getLogger(__name__)


# Pinned to the project's compatible fork. Override per-invocation with
# ``subtitle setup-whisper --repo <url> --ref <branch_or_tag>``.
DEFAULT_REPO_URL = "https://github.com/innovatorved/whisper.cpp.git"
DEFAULT_REF = "develop"


class WhisperSetupError(SubtitleError):
    """Raised when the ``setup-whisper`` build pipeline fails."""


@dataclass
class WhisperSetupResult:
    """Summary of a successful build/install run."""

    binary_path: str
    source_dir: str
    repo_url: str
    ref: str


def _check_dependency(name: str) -> str:
    """Return the absolute path of ``name`` on PATH or raise.

    All toolchain checks happen up-front so we fail before doing any
    network or disk work — a clean error beats half-written state.
    """
    found = shutil.which(name)
    if not found:
        raise WhisperSetupError(
            f"Required build dependency `{name}` was not found on PATH.",
            details={"missing": name},
        )
    return found


def _check_cxx_compiler() -> str:
    """Verify a C++ compiler is available; CMake will pick its own, but
    we surface a friendlier error here than letting cmake fail mid-build.
    """
    for candidate in ("c++", "g++", "clang++", "cl"):
        path = shutil.which(candidate)
        if path:
            return path
    raise WhisperSetupError(
        "No C++ compiler found on PATH (looked for c++, g++, clang++, cl).",
        details={"hint": "Install Xcode CLI tools (macOS), build-essential "
                         "(Linux), or Visual Studio Build Tools (Windows)."},
    )


def _run(
    argv: List[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> None:
    """Run a subprocess, streaming output through ``log_callback``.

    Uses argv lists (never ``shell=True``) and raises
    :class:`WhisperSetupError` on non-zero exit so callers don't have to
    distinguish between :class:`FileNotFoundError` and
    :class:`subprocess.CalledProcessError`.
    """
    pretty = " ".join(argv)
    logger.info("$ %s%s", pretty, f"   (cwd={cwd})" if cwd else "")
    if log_callback:
        log_callback(f"$ {pretty}")

    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise WhisperSetupError(
            f"Could not invoke `{argv[0]}`: not found on PATH.",
            details={"argv": argv},
            cause=e,
        )

    if completed.stdout:
        logger.debug(completed.stdout)
    if completed.stderr:
        logger.debug(completed.stderr)

    if completed.returncode != 0:
        # Surface the actual stderr so users can act on the failure
        # (missing header, OpenMP not found, etc.) rather than a generic
        # "build failed".
        tail = (completed.stderr or completed.stdout or "").strip()
        raise WhisperSetupError(
            f"Command failed (exit {completed.returncode}): {pretty}",
            details={
                "argv": argv,
                "cwd": cwd,
                "stderr_tail": tail[-2000:] if tail else "",
            },
        )


def _git_already_at(src_dir: str, repo_url: str) -> bool:
    """Return True iff ``src_dir`` is a git repo whose ``origin`` matches."""
    git_dir = os.path.join(src_dir, ".git")
    if not os.path.isdir(git_dir):
        return False
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=src_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    # Tolerate ssh-vs-https and trailing-.git differences.
    norm_local = out.rstrip("/").removesuffix(".git").lower()
    norm_repo = repo_url.rstrip("/").removesuffix(".git").lower()
    return norm_local.endswith(norm_repo.split("github.com/")[-1])


def setup_whisper(
    repo_url: str = DEFAULT_REPO_URL,
    ref: str = DEFAULT_REF,
    force: bool = False,
    pull: bool = True,
    log_callback: Optional[Callable[[str], None]] = None,
) -> WhisperSetupResult:
    """Clone, build, and install whisper.cpp into the user data dir.

    Args:
        repo_url: Git URL of the whisper.cpp source. Defaults to the
            project's compatible fork.
        ref: Branch, tag, or commit to check out.
        force: If True, wipe any existing source tree and start clean.
        pull: If False, skip ``git fetch / pull`` for an existing checkout
            (useful for reproducible offline rebuilds).
        log_callback: Optional callable for streaming human-readable
            progress lines to the CLI.

    Returns:
        :class:`WhisperSetupResult` with the absolute binary path.

    Raises:
        WhisperSetupError: With actionable details if any step fails.
    """
    # 1. Toolchain pre-flight. Done before any network / disk work so we
    #    bail fast on missing deps without leaving half-built state.
    git = _check_dependency("git")
    cmake = _check_dependency("cmake")
    _check_cxx_compiler()

    data_dir = default_data_dir()
    src_dir = os.path.join(data_dir, "whisper.cpp")
    bin_target = installed_whisper_binary_target()
    bin_dir = os.path.dirname(bin_target)
    build_dir = os.path.join(src_dir, "build")

    os.makedirs(data_dir, exist_ok=True)

    if log_callback:
        log_callback(f"[setup-whisper] data dir: {data_dir}")
        log_callback(f"[setup-whisper] repo:     {repo_url}@{ref}")

    # 2. Clone (or refresh) the source tree.
    if force and os.path.isdir(src_dir):
        if log_callback:
            log_callback("[setup-whisper] --force: removing existing checkout")
        shutil.rmtree(src_dir)

    if not os.path.isdir(src_dir):
        if log_callback:
            log_callback(f"[setup-whisper] cloning {repo_url}")
        _run(
            [git, "clone", "--depth", "1", "--branch", ref, repo_url, src_dir],
            log_callback=log_callback,
        )
    else:
        if not _git_already_at(src_dir, repo_url):
            raise WhisperSetupError(
                f"Existing checkout at {src_dir} points at a different "
                f"remote. Re-run with --force to wipe and re-clone.",
                details={"src_dir": src_dir, "expected_remote": repo_url},
            )
        if pull:
            if log_callback:
                log_callback(f"[setup-whisper] updating {src_dir} -> {ref}")
            _run([git, "fetch", "--depth", "1", "origin", ref],
                 cwd=src_dir, log_callback=log_callback)
            _run([git, "checkout", ref],
                 cwd=src_dir, log_callback=log_callback)
            # Hard reset to remote ref so local edits never block a build.
            _run([git, "reset", "--hard", f"origin/{ref}"],
                 cwd=src_dir, log_callback=log_callback)

    # 3. Configure + build with CMake. CMake is more portable than the
    #    bare Makefile (it handles MSVC on Windows) and matches what
    #    upstream whisper.cpp recommends for >=1.7.x.
    if log_callback:
        log_callback("[setup-whisper] configuring with cmake")
    _run(
        [
            cmake,
            "-B", build_dir,
            "-S", src_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            # Keep examples (whisper-cli is one of them) on by default.
            "-DBUILD_SHARED_LIBS=OFF",
            "-DWHISPER_BUILD_EXAMPLES=ON",
            "-DWHISPER_BUILD_TESTS=OFF",
        ],
        log_callback=log_callback,
    )

    if log_callback:
        log_callback("[setup-whisper] building (this takes ~30-90s)")
    build_argv = [cmake, "--build", build_dir, "--config", "Release"]
    if sys.platform != "win32":
        # CMake on Unix passes -j through to the underlying generator;
        # on Windows MSBuild has its own /m flag and ignores -j.
        build_argv.extend(["-j"])
    _run(build_argv, log_callback=log_callback)

    # 4. Locate the freshly-built binary. CMake puts examples in
    #    build/bin/<config>/ on multi-config generators (MSVC) and
    #    build/bin/ on single-config (Unix Makefiles, Ninja).
    candidates = [
        os.path.join(build_dir, "bin", "whisper-cli"),
        os.path.join(build_dir, "bin", "whisper-cli.exe"),
        os.path.join(build_dir, "bin", "Release", "whisper-cli.exe"),
        os.path.join(build_dir, "bin", "Release", "whisper-cli"),
        os.path.join(src_dir, "whisper-cli"),  # legacy Makefile output
        os.path.join(src_dir, "main"),         # very old upstream name
    ]
    built = next(
        (p for p in candidates if os.path.isfile(p) and os.access(p, os.X_OK)),
        None,
    )
    if not built:
        raise WhisperSetupError(
            "Build succeeded but the whisper-cli binary could not be located.",
            details={"searched": candidates, "build_dir": build_dir},
        )

    # 5. Install into the canonical user-data location. We copy (not
    #    symlink) so the binary is independent of a `--force`-driven
    #    rebuild that wipes ``src_dir``.
    os.makedirs(bin_dir, exist_ok=True)
    if os.path.exists(bin_target):
        os.remove(bin_target)
    shutil.copy2(built, bin_target)
    os.chmod(bin_target, 0o755)

    # 6. Smoke-test the installed binary so we don't return success on
    #    something that won't run (wrong glibc, broken signing, etc.).
    try:
        subprocess.run(
            [bin_target, "-h"],
            check=True,
            capture_output=True,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise WhisperSetupError(
            f"Installed binary at {bin_target} did not pass `-h` smoke test.",
            details={"binary": bin_target},
            cause=e,
        )

    if log_callback:
        log_callback(f"[setup-whisper] installed: {bin_target}")

    return WhisperSetupResult(
        binary_path=bin_target,
        source_dir=src_dir,
        repo_url=repo_url,
        ref=ref,
    )
