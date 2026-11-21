"""
Download utilities.

Provides functions for downloading files from URLs, including
support for progress tracking and various URL types.
"""

import logging
import os
import urllib.parse
import urllib.request
import uuid
from typing import Optional, Callable

from tqdm import tqdm

from .exceptions import DownloadError

logger = logging.getLogger(__name__)


def is_google_drive_url(url: str) -> bool:
    """Return True if the URL points to Google Drive."""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        return host in {"drive.google.com", "docs.google.com"}
    except ValueError:
        return False


def is_url(path: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        path: String to check
        
    Returns:
        True if path is a valid URL, False otherwise
    """
    try:
        result = urllib.parse.urlparse(path)
        return result.scheme in {"http", "https"} and bool(result.netloc)
    except ValueError:
        return False


def download_file(
    url: str,
    output_path: Optional[str] = None,
    show_progress: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Download a file from a URL (including Google Drive links).
    
    Args:
        url: URL to download from
        output_path: Optional custom output path
        show_progress: Whether to show progress bar
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
        output_dir: Optional directory to place auto-named downloads in
        
    Returns:
        Path to the downloaded file
        
    Raises:
        DownloadError: If download fails
    """
    # Content-Type to extension mapping
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
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get("Content-Length", 0) or 0)
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()

            if output_path is None:
                parsed = urllib.parse.urlparse(url)
                filename = os.path.basename(urllib.parse.unquote(parsed.path))
                if not filename:
                    filename = str(uuid.uuid4())
                
                _, ext = os.path.splitext(filename)
                if not ext or ext.lower() not in {".mp4", ".mkv", ".avi", ".mov", ".webm", 
                                                   ".flv", ".wmv", ".mpeg", ".mpg", ".m4v",
                                                   ".mp3", ".wav", ".ogg", ".flac", ".aac", 
                                                   ".m4a", ".wma"}:
                    if content_type in CONTENT_TYPE_MAP:
                        filename = filename + CONTENT_TYPE_MAP[content_type]
                    else:
                        filename = filename + ".mp4"
                        logger.info("No extension detected, defaulting to .mp4")
                
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                else:
                    output_path = filename
            else:
                parent = os.path.dirname(os.path.abspath(output_path))
                if parent:
                    os.makedirs(parent, exist_ok=True)

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
                with open(output_path, "wb") as out_f:
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
        
        logger.info(f"Downloaded: {output_path}")
        return output_path
        
    except DownloadError:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise DownloadError(f"Failed to download {url}: {e}", details={"url": url}, cause=e)


def download_with_gdown(url: str, output_path: str) -> str:
    """
    Download a file from Google Drive using gdown.
    
    Args:
        url: Google Drive URL
        output_path: Path to save the file
        
    Returns:
        Path to the downloaded file
        
    Raises:
        DownloadError: If download fails
    """
    try:
        import gdown
        result = gdown.download(url, output_path, quiet=False, fuzzy=True)
        if not result:
            raise DownloadError(f"gdown failed to download {url}", details={"url": url})
        logger.info(f"Downloaded from Google Drive: {result}")
        return result
    except ImportError as e:
        logger.error("gdown not installed. Install with: pip install gdown")
        raise DownloadError("gdown package not installed", cause=e)
    except DownloadError:
        raise
    except Exception as e:
        logger.error(f"Google Drive download failed: {e}")
        raise DownloadError(
            f"Failed to download from Google Drive: {e}",
            details={"url": url},
            cause=e,
        )


def get_url_filename(url: str, default: str = "download") -> str:
    """
    Extract filename from a URL.
    
    Args:
        url: URL to extract filename from
        default: Default filename if extraction fails
        
    Returns:
        Extracted filename or default
    """
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        filename = os.path.basename(path)
        return filename if filename else default
    except Exception:
        return default
