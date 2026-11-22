"""Install whisper-cli into the user data dir for `subtitle setup-whisper`.

Strategy:
1. Try downloading a prebuilt platform binary from GitHub Releases
   (``innovatorved/subtitle``) with optional SHA-256 verification (~2 seconds,
   zero compiler toolchain needed on macOS, Linux, or Windows).
2. Fall back automatically to cloning and building ``innovatorved/whisper.cpp``
   via CMake with auto-detected GPU acceleration (Metal / CUDA / Vulkan).
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional

from .exceptions import SubtitleError
from .paths import default_data_dir, installed_whisper_binary_target

logger = logging.getLogger(__name__)

DEFAULT_REPO_URL = "https://github.com/innovatorved/whisper.cpp.git"
DEFAULT_REF = "develop"
DEFAULT_RELEASE_REPO = "innovatorved/subtitle"
PREBUILT_TAG = "whisper-binaries"


class WhisperSetupError(SubtitleError):
    """Raised when the setup-whisper install/build pipeline fails."""


@dataclass
class WhisperSetupResult:
    binary_path: str
    source_dir: str
    repo_url: str
    ref: str
    method: str = "source"  # "prebuilt" or "source"
    gpu_backend: str = "auto"


def detect_platform_asset_name() -> Optional[str]:
    """Return the prebuilt release asset name for the current OS & CPU arch."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    if machine in {"x86_64", "amd64"}:
        arch = "x86_64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        return None

    if sys_name == "darwin":
        return f"whisper-cli-darwin-{arch}"
    if sys_name == "linux":
        return f"whisper-cli-linux-{arch}"
    if sys_name == "windows" and arch == "x86_64":
        return "whisper-cli-windows-x86_64.exe"
    return None


def _download_to_file(url: str, dest: str, timeout: int = 30) -> None:
    part = f"{dest}.part"
    req = urllib.request.Request(url, headers={"User-Agent": "subtitle-generator/4.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(part, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        os.replace(part, dest)
    except Exception:
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
        raise


def _verify_sha256(file_path: str, expected_hex: str) -> bool:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected_hex.strip().split()[0].lower()


def try_download_prebuilt(
    bin_target: str,
    release_repo: str = DEFAULT_RELEASE_REPO,
    tag: str = PREBUILT_TAG,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """Attempt to download a prebuilt whisper-cli binary for this platform."""
    asset = detect_platform_asset_name()
    if not asset:
        return None

    base_url = f"https://github.com/{release_repo}/releases/download/{tag}"
    bin_url = f"{base_url}/{asset}"
    sha_url = f"{bin_url}.sha256"

    os.makedirs(os.path.dirname(bin_target), exist_ok=True)
    if log_callback:
        log_callback(f"[setup-whisper] checking prebuilt binary: {asset}")

    try:
        _download_to_file(bin_url, bin_target, timeout=30)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.info("Prebuilt binary unavailable (%s); will build from source.", e)
        if log_callback:
            log_callback(f"[setup-whisper] prebuilt not available ({e}); falling back to source build")
        return None

    # Best-effort SHA-256 verification if checksum asset exists
    try:
        req = urllib.request.Request(sha_url, headers={"User-Agent": "subtitle-generator/4.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            expected_sha = resp.read().decode("utf-8", errors="replace").strip()
        if expected_sha and not _verify_sha256(bin_target, expected_sha):
            os.remove(bin_target)
            raise WhisperSetupError(
                f"SHA-256 checksum mismatch for prebuilt binary {asset}",
                details={"url": bin_url},
            )
        if log_callback:
            log_callback("[setup-whisper] SHA-256 checksum verified")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            logger.warning("Checksum fetch failed: %s", e)
    except WhisperSetupError:
        raise
    except Exception as e:
        logger.debug("Skipping checksum check: %s", e)

    if sys.platform != "win32":
        os.chmod(bin_target, 0o755)

    try:
        subprocess.run([bin_target, "-h"], check=True, capture_output=True, timeout=15)
        return bin_target
    except Exception as e:
        logger.warning("Prebuilt binary smoke test failed (%s); falling back to source build.", e)
        if os.path.exists(bin_target):
            try:
                os.remove(bin_target)
            except OSError:
                pass
        return None


def _check_dependency(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise WhisperSetupError(
            f"Required build dependency `{name}` not found on PATH.",
            details={"missing": name},
        )
    return found


def _has_windows_msvc() -> bool:
    """Detect Visual Studio Build Tools on Windows via vswhere.exe."""
    if sys.platform != "win32":
        return False
    prog_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(prog_x86, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.isfile(vswhere):
        return False
    try:
        out = subprocess.check_output(
            [vswhere, "-latest", "-products", "*", "-property", "installationPath"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        ).strip()
        return bool(out)
    except Exception:
        return False


def _check_cxx_compiler() -> str:
    for candidate in ("c++", "g++", "clang++", "cl"):
        path = shutil.which(candidate)
        if path:
            return path
    if _has_windows_msvc():
        return "msvc (via Visual Studio)"
    raise WhisperSetupError(
        "No C++ compiler found on PATH (looked for c++, g++, clang++, cl).",
        details={"hint": "Install Xcode CLI tools, build-essential, or VS Build Tools."},
    )


def _rmtree_force(path: str) -> None:
    """Remove a directory tree even when Windows marks .git objects read-only."""
    import stat

    def _handle_readonly(func, p, _exc_info):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            func(p)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_handle_readonly)


def _detect_cmake_gpu_flags(gpu: str = "auto") -> tuple[list[str], str]:
    """Return CMake GPU flags and resolved backend name."""
    mode = (gpu or "auto").lower()
    if mode == "cpu":
        return (["-DGGML_CUDA=OFF", "-DGGML_VULKAN=OFF", "-DGGML_METAL=OFF"], "cpu")
    if mode == "cuda":
        return (["-DGGML_CUDA=ON"], "cuda")
    if mode == "vulkan":
        return (["-DGGML_VULKAN=ON"], "vulkan")
    if mode == "metal":
        return (["-DGGML_METAL=ON", "-DGGML_METAL_EMBED_LIBRARY=ON"], "metal")

    # Auto-detect
    if sys.platform == "darwin":
        return (["-DGGML_METAL=ON", "-DGGML_METAL_EMBED_LIBRARY=ON"], "metal")
    if shutil.which("nvcc"):
        return (["-DGGML_CUDA=ON"], "cuda")
    if os.environ.get("VULKAN_SDK") or shutil.which("glslc"):
        return (["-DGGML_VULKAN=ON"], "vulkan")
    return ([], "cpu")


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
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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


def _git_head_rev(src_dir: str) -> Optional[str]:
    if not os.path.isdir(os.path.join(src_dir, ".git")):
        return None
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=src_dir,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_already_at(src_dir: str, repo_url: str) -> bool:
    if not os.path.isdir(os.path.join(src_dir, ".git")):
        return False
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=src_dir,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
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
    from_source: bool = False,
    gpu: str = "auto",
    log_callback: Optional[Callable[[str], None]] = None,
) -> WhisperSetupResult:
    """Install whisper-cli (prebuilt binary first, with CMake source-build fallback)."""
    data_dir = default_data_dir()
    src_dir = os.path.join(data_dir, "whisper.cpp")
    bin_target = installed_whisper_binary_target()
    bin_dir = os.path.dirname(bin_target)
    build_dir = os.path.join(src_dir, "build")

    os.makedirs(data_dir, exist_ok=True)
    if log_callback:
        log_callback(f"[setup-whisper] data dir: {data_dir}")

    # Step 1: Fast-path prebuilt binary download (unless custom repo/ref or --from-source)
    use_prebuilt = (
        not from_source
        and repo_url == DEFAULT_REPO_URL
        and ref == DEFAULT_REF
        and gpu == "auto"
    )
    if use_prebuilt:
        downloaded = try_download_prebuilt(bin_target, log_callback=log_callback)
        if downloaded:
            if log_callback:
                log_callback(f"[setup-whisper] installed prebuilt binary: {downloaded}")
            return WhisperSetupResult(
                binary_path=downloaded,
                source_dir="",
                repo_url=f"https://github.com/{DEFAULT_RELEASE_REPO}",
                ref=PREBUILT_TAG,
                method="prebuilt",
                gpu_backend="auto",
            )

    # Step 2: Source build fallback
    git = _check_dependency("git")
    cmake = _check_dependency("cmake")
    _check_cxx_compiler()

    if log_callback:
        log_callback(f"[setup-whisper] repo:     {repo_url}@{ref}")

    if force and os.path.isdir(src_dir):
        if log_callback:
            log_callback("[setup-whisper] --force: removing existing checkout")
        _rmtree_force(src_dir)

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
            old_head = _git_head_rev(src_dir)
            if log_callback:
                log_callback(f"[setup-whisper] updating {src_dir} -> {ref}")
            _run([git, "fetch", "--depth", "1", "origin", ref], cwd=src_dir, log_callback=log_callback)
            _run([git, "checkout", ref], cwd=src_dir, log_callback=log_callback)
            _run([git, "reset", "--hard", f"origin/{ref}"], cwd=src_dir, log_callback=log_callback)
            new_head = _git_head_rev(src_dir)
            if old_head != new_head and os.path.isdir(build_dir):
                if log_callback:
                    log_callback("[setup-whisper] source updated; clearing stale CMake build dir")
                shutil.rmtree(build_dir)

    gpu_flags, resolved_gpu = _detect_cmake_gpu_flags(gpu)
    if log_callback:
        log_callback(f"[setup-whisper] configuring with cmake (backend={resolved_gpu})")
    _run(
        [
            cmake,
            "-B", build_dir,
            "-S", src_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DWHISPER_BUILD_EXAMPLES=ON",
            "-DWHISPER_BUILD_TESTS=OFF",
            *gpu_flags,
        ],
        log_callback=log_callback,
    )

    if log_callback:
        log_callback("[setup-whisper] building (~30-90s)")
    build_argv = [cmake, "--build", build_dir, "--config", "Release"]
    if sys.platform != "win32":
        build_argv.append("-j")
    else:
        build_argv.extend(["--parallel"])
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
    if sys.platform != "win32":
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
        method="source",
        gpu_backend=resolved_gpu,
    )
