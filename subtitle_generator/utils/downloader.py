"""Download utilities for direct media URLs, Google Drive, and YouTube/social URLs."""

from __future__ import annotations

import logging
import os
import urllib.parse
import urllib.request
import uuid
from typing import Callable, Optional

from tqdm import tqdm

from .exceptions import DownloadError

logger = logging.getLogger(__name__)

_YT_DLP_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "vimeo.com",
    "www.vimeo.com",
    "tiktok.com",
    "www.tiktok.com",
    "instagram.com",
    "www.instagram.com",
    "twitter.com",
    "x.com",
    "twitch.tv",
    "www.twitch.tv",
    "dailymotion.com",
    "soundcloud.com",
}


def is_google_drive_url(url: str) -> bool:
    """Return True if the URL points to Google Drive."""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        return host in {"drive.google.com", "docs.google.com"}
    except ValueError:
        return False


def is_yt_dlp_url(url: str) -> bool:
    """Return True if the URL is from a streaming platform handled by yt-dlp."""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        return host in _YT_DLP_HOSTS or any(host.endswith("." + h) for h in _YT_DLP_HOSTS)
    except ValueError:
        return False


def is_url(path: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    try:
        result = urllib.parse.urlparse(path)
        return result.scheme in {"http", "https"} and bool(result.netloc)
    except ValueError:
        return False


def download_with_yt_dlp(
    url: str,
    output_dir: Optional[str] = None,
    audio_only: bool = False,
) -> str:
    """Download media from YouTube/TikTok/Vimeo/etc. using optional `yt-dlp`."""
    try:
        import yt_dlp  # type: ignore
    except ImportError as e:
        raise DownloadError(
            "Downloading from YouTube/streaming platforms requires `yt-dlp`. "
            "Install with: pip install 'subtitle-generator[yt]'",
            details={"url": url},
            cause=e,
        )

    target_dir = output_dir or "."
    os.makedirs(target_dir, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    outtmpl = os.path.join(target_dir, f"sg_{uid}_%(title).80s.%(ext)s")

    ydl_opts: dict = {
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best" if audio_only else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info)
            if not os.path.isfile(downloaded_path):
                # yt-dlp may merge into .mp4 or .mkv
                base, _ = os.path.splitext(downloaded_path)
                for ext in (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".opus"):
                    if os.path.isfile(base + ext):
                        downloaded_path = base + ext
                        break
            if not os.path.isfile(downloaded_path):
                raise DownloadError(f"yt-dlp completed but output file not found for {url}")
            logger.info("Downloaded via yt-dlp: %s", downloaded_path)
            return downloaded_path
    except DownloadError:
        raise
    except Exception as e:
        raise DownloadError(
            f"yt-dlp failed to download {url}: {e}",
            details={"url": url},
            cause=e,
        )


def download_file(
    url: str,
    output_path: Optional[str] = None,
    show_progress: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    output_dir: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """Download a file from a URL (direct HTTP, Google Drive, or yt-dlp platforms)."""
    CONTENT_TYPE_MAP = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/x-msvideo": ".avi",
        "video/quicktime": ".mov",
        "video/x-matroska": ".mkv",
        "video/x-flv": ".flv",
        "video/x-ms-wmv": ".wmv",
        "video/mpeg": ".mpeg",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
        "audio/aac": ".aac",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
    }

    if is_google_drive_url(url):
        if output_path is None:
            target_dir = output_dir or "."
            os.makedirs(target_dir, exist_ok=True)
            output_path = os.path.join(target_dir, f"{uuid.uuid4()}.mp4")
        return download_with_gdown(url, output_path)

    if is_yt_dlp_url(url):
        return download_with_yt_dlp(url, output_dir=output_dir)

    part_path: Optional[str] = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "subtitle-generator/4.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            total_size = int(response.headers.get("Content-Length", 0) or 0)
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()

            if output_path is None:
                from .file_handler import sanitize_filename

                parsed = urllib.parse.urlparse(url)
                raw_name = os.path.basename(urllib.parse.unquote(parsed.path))
                filename = sanitize_filename(raw_name) if raw_name else str(uuid.uuid4())
                if not filename:
                    filename = str(uuid.uuid4())

                _, ext = os.path.splitext(filename)
                if not ext or ext.lower() not in {
                    ".mp4", ".mkv", ".avi", ".mov", ".webm",
                    ".flv", ".wmv", ".mpeg", ".mpg", ".m4v",
                    ".mp3", ".wav", ".ogg", ".flac", ".aac",
                    ".m4a", ".wma",
                }:
                    if content_type in CONTENT_TYPE_MAP:
                        filename = filename + CONTENT_TYPE_MAP[content_type]
                    else:
                        filename = filename + ".mp4"
                        logger.info("No extension detected, defaulting to .mp4")

                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
                else:
                    output_path = filename
            else:
                parent = os.path.dirname(os.path.abspath(output_path))
                if parent:
                    os.makedirs(parent, exist_ok=True)

            part_path = f"{output_path}.part"
            chunk_size = 64 * 1024
            downloaded = 0
            pbar = (
                tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    miniters=1,
                    desc=os.path.basename(output_path),
                    total=total_size or None,
                )
                if show_progress
                else None
            )
            try:
                with open(part_path, "wb") as out_f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        if pbar is not None:
                            pbar.update(len(chunk))
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            finally:
                if pbar is not None:
                    pbar.close()

            os.replace(part_path, output_path)

        logger.info("Downloaded: %s", output_path)
        return output_path

    except DownloadError:
        raise
    except Exception as e:
        if part_path and os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass
        logger.error("Download failed: %s", e)
        raise DownloadError(f"Failed to download {url}: {e}", details={"url": url}, cause=e)


def download_with_gdown(url: str, output_path: str) -> str:
    """Download a file from Google Drive using optional `gdown`."""
    try:
        import gdown  # type: ignore
    except ImportError as e:
        raise DownloadError(
            "Google Drive downloads require `gdown`. "
            "Install with: pip install 'subtitle-generator[gdrive]'",
            details={"url": url},
            cause=e,
        )
    try:
        result = gdown.download(url, output_path, quiet=False, fuzzy=True)
        if not result:
            raise DownloadError(f"gdown failed to download {url}", details={"url": url})
        logger.info("Downloaded from Google Drive: %s", result)
        return result
    except DownloadError:
        raise
    except Exception as e:
        logger.error("Google Drive download failed: %s", e)
        raise DownloadError(
            f"Failed to download from Google Drive: {e}",
            details={"url": url},
            cause=e,
        )


def get_url_filename(url: str, default: str = "download") -> str:
    """Extract filename from a URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        filename = os.path.basename(path)
        return filename if filename else default
    except Exception:
        return default
