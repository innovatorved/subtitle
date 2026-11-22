"""Model manager for Whisper and Silero VAD models.

Provides centralized model downloading, caching, HTTP Range resume,
SHA-256 verification, and thread-safe path resolution.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import urllib.error
import urllib.request
from threading import Lock
from typing import Optional

from tqdm import tqdm

logger = logging.getLogger(__name__)


class ModelManager:
    """Thread-safe model manager for Whisper and Silero VAD models.

    Instances are cached per normalized ``models_dir`` so calling
    ``ModelManager(models_dir="/custom")`` never silently returns an
    instance bound to a different directory.
    """

    _instances: dict[str, "ModelManager"] = {}
    _instance: Optional["ModelManager"] = None
    _lock = Lock()
    _download_lock = Lock()
    _initialized: bool = False

    # Available Whisper models
    MODELS = [
        "tiny.en",
        "tiny",
        "tiny-q5_1",
        "tiny.en-q5_1",
        "tiny-q8_0",
        "tiny.en-q8_0",
        "base.en",
        "base",
        "base-q5_1",
        "base.en-q5_1",
        "base-q8_0",
        "base.en-q8_0",
        "small.en",
        "small.en-tdrz",
        "small",
        "small-q5_1",
        "small.en-q5_1",
        "small-q8_0",
        "small.en-q8_0",
        "medium",
        "medium.en",
        "medium-q5_0",
        "medium.en-q5_0",
        "medium-q8_0",
        "medium.en-q8_0",
        "large-v1",
        "large-v2",
        "large-v2-q5_0",
        "large-v2-q8_0",
        "large-v3",
        "large-v3-q5_0",
        "large-v3-turbo",
        "large-v3-turbo-q5_0",
        "large-v3-turbo-q8_0",
        "turbo",
        "large",
        "large-q5_0",
    ]

    # Silero VAD model (used by whisper.cpp --vad)
    SILERO_VAD_NAME = "silero-vad"
    SILERO_VAD_FILENAME = "ggml-silero-v5.1.2.bin"
    SILERO_VAD_URL = (
        "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin"
    )

    MODEL_FILENAMES = {
        **{model: f"ggml-{model}.bin" for model in MODELS},
        "large": "ggml-large-v3.bin",
        "large-q5_0": "ggml-large-v3-q5_0.bin",
        "turbo": "ggml-large-v3-turbo.bin",
        SILERO_VAD_NAME: SILERO_VAD_FILENAME,
    }

    # Optional known SHA-256 checksums for integrity verification
    MODEL_SHA256: dict[str, str] = {}

    DEFAULT_SOURCE = "https://huggingface.co/ggerganov/whisper.cpp"
    TDRZ_SOURCE = "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"

    def __new__(cls, models_dir: Optional[str] = None):
        """Return a cached instance keyed by normalized models_dir."""
        from ..utils.paths import default_models_dir

        resolved_dir = os.path.abspath(
            os.path.expanduser(models_dir if models_dir else default_models_dir())
        )
        with cls._lock:
            existing = cls._instances.get(resolved_dir)
            if existing is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[resolved_dir] = instance
                cls._instance = instance
                return instance
            cls._instance = existing
            return existing

    def __init__(self, models_dir: Optional[str] = None):
        if self._initialized:
            return

        from ..utils.paths import default_models_dir

        self.models_dir = models_dir if models_dir else default_models_dir()
        self._ensure_models_dir()
        self._initialized = True
        logger.info("ModelManager initialized with models_dir: %s", self.models_dir)

    def _ensure_models_dir(self) -> None:
        try:
            os.makedirs(self.models_dir, exist_ok=True)
        except OSError as e:
            from ..utils.paths import default_models_dir

            fallback = default_models_dir()
            if fallback != self.models_dir:
                logger.warning(
                    "Cannot create models dir %s (%s); falling back to %s",
                    self.models_dir,
                    e,
                    fallback,
                )
                self.models_dir = fallback
                os.makedirs(self.models_dir, exist_ok=True)
            else:
                raise

    def get_model(self, name: str) -> str:
        """Get model path, downloading if necessary."""
        if name not in self.MODELS:
            raise ValueError(
                f"Invalid model: {name}. Available: {', '.join(self.MODELS)}"
            )

        model_path = self.get_model_path(name)
        if not os.path.exists(model_path):
            logger.info("Model '%s' not found locally, downloading...", name)
            self.download_model(name)
        return model_path

    def get_vad_model(self) -> str:
        """Get path to the Silero VAD GGML model, downloading (~885 KB) if needed."""
        vad_path = os.path.join(self.models_dir, self.SILERO_VAD_FILENAME)
        if os.path.exists(vad_path) and os.path.getsize(vad_path) > 0:
            return vad_path

        with self._download_lock:
            if os.path.exists(vad_path) and os.path.getsize(vad_path) > 0:
                return vad_path
            logger.info("Downloading Silero VAD model to %s...", vad_path)
            self._download_file_with_retry(self.SILERO_VAD_URL, vad_path)
            return vad_path

    def get_model_path(self, name: str) -> str:
        filename = self.MODEL_FILENAMES.get(name, f"ggml-{name}.bin")
        return os.path.join(self.models_dir, filename)

    def model_exists(self, name: str) -> bool:
        path = self.get_model_path(name)
        return os.path.exists(path) and os.path.getsize(path) > 0

    def download_model(self, name: str, force: bool = False) -> str:
        """Download a Whisper model atomically with retry and optional SHA-256 verification."""
        from ..utils.exceptions import ModelError

        if name not in self.MODELS:
            raise ModelError(
                f"Invalid model: {name}",
                details={"available_models": self.MODELS},
            )

        model_path = self.get_model_path(name)
        if os.path.exists(model_path) and not force:
            logger.info("Model '%s' already exists: %s", name, model_path)
            return model_path

        with self._download_lock:
            if os.path.exists(model_path) and not force:
                logger.info("Model '%s' already exists: %s", name, model_path)
                return model_path

            source = self.TDRZ_SOURCE if "tdrz" in name else self.DEFAULT_SOURCE
            filename = self.MODEL_FILENAMES.get(name, f"ggml-{name}.bin")
            url = f"{source}/resolve/main/{filename}"

            logger.info("Downloading model '%s' from %s...", name, source)
            try:
                expected_sha = self.MODEL_SHA256.get(name)
                self._download_file_with_retry(url, model_path, expected_sha256=expected_sha)
                logger.info("Model downloaded: %s", model_path)
                return model_path
            except Exception as e:
                raise ModelError(
                    f"Failed to download model '{name}'",
                    details={"url": url, "model": name},
                    cause=e,
                )

    def _download_file_with_retry(
        self,
        url: str,
        output_path: str,
        max_attempts: int = 3,
        expected_sha256: Optional[str] = None,
    ) -> None:
        delay = 1.0
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                self._download_file(url, output_path, expected_sha256=expected_sha256)
                return
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    logger.warning(
                        "Download failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2

        if last_error is not None:
            raise last_error

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Compute SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _download_file(
        self,
        url: str,
        output_path: str,
        timeout: int = 30,
        expected_sha256: Optional[str] = None,
    ) -> None:
        """Download a file atomically with timeout, Range resume, and progress bar."""
        filename = os.path.basename(output_path)
        part_path = f"{output_path}.part"
        existing_bytes = os.path.getsize(part_path) if os.path.exists(part_path) else 0

        headers = {"User-Agent": "subtitle-generator/4.0"}
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"

        try:
            req = urllib.request.Request(url, headers=headers)
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as http_err:
                if http_err.code == 416 and existing_bytes > 0:
                    # Stale .part >= remote file size; restart cleanly from byte 0
                    if os.path.exists(part_path):
                        os.remove(part_path)
                    existing_bytes = 0
                    req = urllib.request.Request(url, headers={"User-Agent": "subtitle-generator/4.0"})
                    resp = urllib.request.urlopen(req, timeout=timeout)
                else:
                    raise

            with resp:
                status = getattr(resp, "status", 200)
                if status == 206 and existing_bytes > 0:
                    mode = "ab"
                    initial = existing_bytes
                    content_len = int(resp.headers.get("Content-Length", 0) or 0)
                    total = (initial + content_len) if content_len > 0 else None
                else:
                    mode = "wb"
                    initial = 0
                    content_len = int(resp.headers.get("Content-Length", 0) or 0)
                    total = content_len if content_len > 0 else None

                with tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    miniters=1,
                    desc=filename,
                    total=total,
                    initial=initial,
                ) as pbar:
                    with open(part_path, mode) as out_f:
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            pbar.update(len(chunk))

            if expected_sha256:
                actual_sha = self.compute_sha256(part_path)
                if actual_sha.lower() != expected_sha256.lower():
                    os.remove(part_path)
                    raise ValueError(
                        f"Checksum mismatch for {filename}: expected {expected_sha256}, got {actual_sha}"
                    )

            os.replace(part_path, output_path)
        except Exception:
            if os.path.exists(part_path) and os.path.getsize(part_path) == 0:
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            raise

    def list_available_models(self) -> list[str]:
        return self.MODELS.copy()

    def list_downloaded_models(self) -> list[str]:
        return [name for name in self.MODELS if self.model_exists(name)]

    def get_model_size(self, name: str) -> int:
        model_path = self.get_model_path(name)
        if os.path.exists(model_path):
            return os.path.getsize(model_path)
        return -1

    def delete_model(self, name: str) -> bool:
        model_path = self.get_model_path(name)
        if os.path.exists(model_path):
            os.remove(model_path)
            logger.info("Deleted model: %s", name)
            return True
        return False

    @classmethod
    def reset_instance(cls) -> None:
        """Reset all cached instances (for testing)."""
        with cls._lock:
            cls._instances.clear()
            cls._instance = None
