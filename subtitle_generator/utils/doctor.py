"""Environment & hardware diagnostics for ``subtitle doctor``."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Optional

from .. import __version__
from .paths import (
    default_config_path,
    default_data_dir,
    default_models_dir,
    default_threads,
    find_ffmpeg_binary,
    find_ffprobe_binary,
    find_whisper_binary,
)


def _probe_binary_output(argv: list[str], timeout: int = 5) -> str:
    try:
        proc = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        return (out + "\n" + err).strip()
    except Exception:
        return ""


def detect_gpu_acceleration() -> dict[str, Any]:
    """Detect available GPU acceleration backends on the current platform."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    backends: list[str] = []

    if sys_name == "darwin" and machine in {"arm64", "aarch64"}:
        backends.append("metal (Apple Silicon)")
    elif sys_name == "darwin":
        backends.append("metal (macOS)")

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        out = _probe_binary_output(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"]
        )
        if out:
            gpu_name = out.splitlines()[0].strip()
            backends.append(f"cuda ({gpu_name})")

    if shutil.which("vulkaninfo") or os.environ.get("VULKAN_SDK"):
        backends.append("vulkan")

    return {
        "available": bool(backends),
        "backends": backends or ["cpu"],
    }


def detect_ffmpeg_hw_encoders(ffmpeg_bin: Optional[str]) -> list[str]:
    """Probe FFmpeg for supported hardware H.264 encoders."""
    if not ffmpeg_bin:
        return []
    out = _probe_binary_output([ffmpeg_bin, "-hide_banner", "-encoders"])
    candidates = ("h264_videotoolbox", "h264_nvenc", "h264_vaapi", "h264_qsv", "h264_amf")
    return [enc for enc in candidates if enc in out]


def _check_optional_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def run_diagnostics(
    whisper_binary: Optional[str] = None,
    models_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Collect a structured diagnostic report for the current environment."""
    resolved_whisper = find_whisper_binary(whisper_binary)
    whisper_caps: dict[str, bool] = {}
    whisper_version = ""
    if resolved_whisper:
        help_text = _probe_binary_output([resolved_whisper, "-h"])
        whisper_caps = {
            "video_input": "-vi" in help_text or "--video-input" in help_text,
            "vad": "--vad" in help_text,
            "progress": "-pp" in help_text or "--print-progress" in help_text,
            "dtw_word_timestamps": "-dtw" in help_text,
            "tinydiarize": "-tdrz" in help_text or "--tinydiarize" in help_text,
            "json_full": "-ojf" in help_text or "--output-json-full" in help_text,
        }
        ver_text = _probe_binary_output([resolved_whisper, "--version"])
        whisper_version = ver_text.splitlines()[0].strip() if ver_text else ""

    ffmpeg_bin = find_ffmpeg_binary()
    ffprobe_bin = find_ffprobe_binary()
    ffmpeg_version = ""
    if ffmpeg_bin:
        ver_out = _probe_binary_output([ffmpeg_bin, "-version"])
        ffmpeg_version = ver_out.splitlines()[0].strip() if ver_out else ""

    effective_models_dir = models_dir or default_models_dir()
    downloaded_models: list[str] = []
    if os.path.isdir(effective_models_dir):
        downloaded_models = sorted(
            f for f in os.listdir(effective_models_dir) if f.endswith(".bin")
        )

    free_gb: Optional[float] = None
    try:
        check_path = effective_models_dir if os.path.exists(effective_models_dir) else os.path.expanduser("~")
        usage = shutil.disk_usage(check_path)
        free_gb = round(usage.free / (1024**3), 2)
    except OSError:
        pass

    gpu = detect_gpu_acceleration()
    hw_encoders = detect_ffmpeg_hw_encoders(ffmpeg_bin)
    config_path = default_config_path()

    extras = {
        "imageio_ffmpeg": _check_optional_module("imageio_ffmpeg"),
        "yt_dlp": _check_optional_module("yt_dlp"),
        "gdown": _check_optional_module("gdown"),
        "faster_whisper": _check_optional_module("faster_whisper"),
        "openai": _check_optional_module("openai"),
        "argostranslate": _check_optional_module("argostranslate"),
    }

    issues: list[str] = []
    if not resolved_whisper:
        issues.append("whisper-cli not found — run `subtitle setup-whisper`.")
    if not ffmpeg_bin:
        issues.append(
            "ffmpeg not found — install ffmpeg or `pip install subtitle-generator[ffmpeg]`."
        )

    return {
        "version": __version__,
        "platform": {
            "os": platform.system(),
            "release": platform.release(),
            "arch": platform.machine(),
            "python": sys.version.split()[0],
            "cpu_count": os.cpu_count() or 1,
            "default_threads": default_threads(),
        },
        "gpu": gpu,
        "whisper_cli": {
            "found": bool(resolved_whisper),
            "path": resolved_whisper,
            "version": whisper_version,
            "capabilities": whisper_caps,
        },
        "ffmpeg": {
            "found": bool(ffmpeg_bin),
            "path": ffmpeg_bin,
            "ffprobe_path": ffprobe_bin,
            "version": ffmpeg_version,
            "hw_encoders": hw_encoders,
        },
        "storage": {
            "data_dir": default_data_dir(),
            "models_dir": effective_models_dir,
            "downloaded_models": downloaded_models,
            "free_disk_gb": free_gb,
            "config_path": config_path,
            "config_exists": os.path.isfile(config_path),
        },
        "extras": extras,
        "issues": issues,
        "healthy": len(issues) == 0,
    }


def format_diagnostics(report: dict[str, Any]) -> str:
    """Render a human-readable diagnostics summary for ``subtitle doctor``."""
    plat = report["platform"]
    w = report["whisper_cli"]
    ff = report["ffmpeg"]
    st = report["storage"]
    gpu = report["gpu"]
    extras = report["extras"]

    lines = [
        f"subtitle-generator v{report['version']} — Environment Diagnostics",
        "=" * 56,
        f"OS / Arch:       {plat['os']} {plat['release']} ({plat['arch']})",
        f"Python:          {plat['python']}",
        f"CPUs / Threads:  {plat['cpu_count']} cores (default -t {plat['default_threads']})",
        f"GPU Backends:    {', '.join(gpu['backends'])}",
        "",
        "Core Binaries:",
        f"  whisper-cli:   {'OK  ' + str(w['path']) if w['found'] else 'MISSING'}",
    ]
    if w["found"]:
        if w["version"]:
            lines.append(f"    version:     {w['version']}")
        caps = ", ".join(k for k, v in w["capabilities"].items() if v) or "basic"
        lines.append(f"    features:    {caps}")
    lines.append(f"  ffmpeg:        {'OK  ' + str(ff['path']) if ff['found'] else 'MISSING'}")
    if ff["found"]:
        lines.append(f"  ffprobe:       {'OK  ' + str(ff['ffprobe_path']) if ff['ffprobe_path'] else 'MISSING'}")
        if ff["hw_encoders"]:
            lines.append(f"    hw encoders: {', '.join(ff['hw_encoders'])}")

    lines.extend([
        "",
        "Storage & Config:",
        f"  models dir:    {st['models_dir']} ({len(st['downloaded_models'])} models)",
        f"  free disk:     {st['free_disk_gb']} GB" if st["free_disk_gb"] is not None else "  free disk:     unknown",
        f"  config file:   {st['config_path']} ({'loaded' if st['config_exists'] else 'not created'})",
        "",
        "Optional Extras:",
    ])
    for name, installed in extras.items():
        mark = "installed" if installed else "not installed"
        lines.append(f"  {name:<15} {mark}")

    lines.append("")
    if report["healthy"]:
        lines.append("Status: READY — all core dependencies are available.")
    else:
        lines.append("Status: ACTION NEEDED")
        for issue in report["issues"]:
            lines.append(f"  - {issue}")

    return "\n".join(lines)
