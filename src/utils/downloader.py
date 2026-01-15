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

logger = logging.getLogger(__name__)


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
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def download_file(
    url: str,
    output_path: Optional[str] = None,
    show_progress: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Download a file from a URL.
    
    Args:
        url: URL to download from
        output_path: Optional custom output path
        show_progress: Whether to show progress bar
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
        
    Returns:
        Path to the downloaded file
        
    Raises:
        Exception: If download fails
    """
    if output_path is None:
        # Generate filename from URL or use UUID
        parsed = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"{uuid.uuid4()}.mp4"
        output_path = filename
    
    try:
        # Set up URL opener with user agent
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)
        
        # Get file info first
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get("Content-Length", 0))
        
        downloaded = [0]  # Use list for closure
        
        def report_hook(block_num: int, block_size: int, total_size: int):
            downloaded[0] += block_size
            if progress_callback:
                progress_callback(downloaded[0], total_size)
        
        if show_progress:
            filename = os.path.basename(output_path)
            with tqdm(
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                miniters=1,
                desc=filename,
                total=total_size,
            ) as pbar:
                def progress_hook(block_num, block_size, total_size):
                    pbar.update(block_size)
                    if progress_callback:
                        progress_callback(pbar.n, total_size)
                
                urllib.request.urlretrieve(url, output_path, reporthook=progress_hook)
        else:
            urllib.request.urlretrieve(url, output_path, reporthook=report_hook)
        
        logger.info(f"Downloaded: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise Exception(f"Failed to download {url}: {e}")


def download_with_gdown(url: str, output_path: str) -> str:
    """
    Download a file from Google Drive using gdown.
    
    Args:
        url: Google Drive URL
        output_path: Path to save the file
        
    Returns:
        Path to the downloaded file
        
    Raises:
        Exception: If download fails
    """
    try:
        import gdown
        gdown.download(url, output_path, quiet=False)
        logger.info(f"Downloaded from Google Drive: {output_path}")
        return output_path
    except ImportError:
        logger.error("gdown not installed. Install with: pip install gdown")
        raise Exception("gdown package not installed")
    except Exception as e:
        logger.error(f"Google Drive download failed: {e}")
        raise Exception(f"Failed to download from Google Drive: {e}")


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
