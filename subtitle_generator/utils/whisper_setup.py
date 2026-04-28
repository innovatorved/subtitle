"""Clone + build whisper.cpp into the user data dir for `subtitle setup-whisper`.

The fork is pinned because upstream whisper.cpp 1.8.x dropped the ``-vi``
flag, breaking direct `.mp4` ingestion.
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
from .paths import default_data_dir, installed_whisper_binary_target

logger = logging.getLogger(__name__)

DEFAULT_REPO_URL = "https://github.com/innovatorved/whisper.cpp.git"
DEFAULT_REF = "develop"


class WhisperSetupError(SubtitleError):
    """Raised when the setup-whisper build pipeline fails."""


@dataclass
class WhisperSetupResult:
    binary_path: str
    source_dir: str
    repo_url: str
    ref: str


def _check_dependency(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise WhisperSetupError(
            f"Required build dependency `{name}` not found on PATH.",
            details={"missing": name},
        )
    return found


def _check_cxx_compiler() -> str:
    for candidate in ("c++", "g++", "clang++", "cl"):
        path = shutil.which(candidate)
        if path:
            return path
    raise WhisperSetupError(
        "No C++ compiler found on PATH (looked for c++, g++, clang++, cl).",
        details={"hint": "Install Xcode CLI tools, build-essential, or VS Build Tools."},
    )


def _run(
    argv: List[str],
    *,
    cwd: Optional[str] = None,
    log_callback: Optional[Callable[[str], None]] = None,
) -> None:
    pretty = " ".join(argv)
    logger.info("$ %s%s", pretty, f"   (cwd={cwd})" if cwd else "")
    if log_callback:
        log_callback(f"$ {pretty}")

    try:
        completed = subprocess.run(
            argv, cwd=cwd, check=False, capture_output=True, text=True
        )
    except FileNotFoundError as e:
        raise WhisperSetupError(
            f"Could not invoke `{argv[0]}`: not found on PATH.",
            details={"argv": argv},
            cause=e,
        )

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()
        raise WhisperSetupError(
            f"Command failed (exit {completed.returncode}): {pretty}",
            details={"argv": argv, "cwd": cwd, "stderr_tail": tail[-2000:]},
        )


def _git_already_at(src_dir: str, repo_url: str) -> bool:
    if not os.path.isdir(os.path.join(src_dir, ".git")):
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
    """Clone, build, and install whisper-cli into the user data dir."""
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
                f"Existing checkout at {src_dir} points at a different remote. "
                f"Re-run with --force to wipe and re-clone.",
                details={"src_dir": src_dir, "expected_remote": repo_url},
            )
        if pull:
            if log_callback:
                log_callback(f"[setup-whisper] updating {src_dir} -> {ref}")
            _run([git, "fetch", "--depth", "1", "origin", ref], cwd=src_dir, log_callback=log_callback)
            _run([git, "checkout", ref], cwd=src_dir, log_callback=log_callback)
            _run([git, "reset", "--hard", f"origin/{ref}"], cwd=src_dir, log_callback=log_callback)

    if log_callback:
        log_callback("[setup-whisper] configuring with cmake")
    _run(
        [
            cmake,
            "-B", build_dir,
            "-S", src_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DWHISPER_BUILD_EXAMPLES=ON",
            "-DWHISPER_BUILD_TESTS=OFF",
        ],
        log_callback=log_callback,
    )

    if log_callback:
        log_callback("[setup-whisper] building (~30-90s)")
    build_argv = [cmake, "--build", build_dir, "--config", "Release"]
    if sys.platform != "win32":
        build_argv.append("-j")
    _run(build_argv, log_callback=log_callback)

    candidates = [
        os.path.join(build_dir, "bin", "whisper-cli"),
        os.path.join(build_dir, "bin", "whisper-cli.exe"),
        os.path.join(build_dir, "bin", "Release", "whisper-cli.exe"),
        os.path.join(build_dir, "bin", "Release", "whisper-cli"),
        os.path.join(src_dir, "whisper-cli"),
        os.path.join(src_dir, "main"),
    ]
    built = next(
        (p for p in candidates if os.path.isfile(p) and os.access(p, os.X_OK)),
        None,
    )
    if not built:
        raise WhisperSetupError(
            "Build succeeded but whisper-cli binary could not be located.",
            details={"searched": candidates, "build_dir": build_dir},
        )

    os.makedirs(bin_dir, exist_ok=True)
    if os.path.exists(bin_target):
        os.remove(bin_target)
    shutil.copy2(built, bin_target)
    os.chmod(bin_target, 0o755)

    try:
        subprocess.run([bin_target, "-h"], check=True, capture_output=True, timeout=15)
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
