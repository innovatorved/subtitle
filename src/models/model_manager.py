"""
Model manager with Singleton pattern.

Provides centralized model management including downloading,
caching, and path resolution for Whisper models.
"""

import logging
import os
import urllib.request
from threading import Lock
from typing import Optional

from tqdm import tqdm

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton model manager for Whisper models.
    
    Handles model downloading, caching, and path resolution.
    Thread-safe implementation using double-checked locking.
    """
    
    _instance: Optional["ModelManager"] = None
    _lock = Lock()
    
    # Available models and their filenames
    MODELS = [
        "tiny.en",
        "tiny",
        "tiny-q5_1",
        "tiny.en-q5_1",
        "base.en",
        "base",
        "base-q5_1",
        "base.en-q5_1",
        "small.en",
        "small.en-tdrz",
        "small",
        "small-q5_1",
        "small.en-q5_1",
        "medium",
        "medium.en",
        "medium-q5_0",
        "medium.en-q5_0",
        "large-v1",
        "large-v2",
        "large",
        "large-q5_0",
    ]
    
    # Model name to filename mapping
    MODEL_FILENAMES = {model: f"ggml-{model}.bin" for model in MODELS}
    
    # Default download sources
    DEFAULT_SOURCE = "https://huggingface.co/ggerganov/whisper.cpp"
    TDRZ_SOURCE = "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"
    
    def __new__(cls, models_dir: str = "models"):
        """Create or return singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance
    
    def __init__(self, models_dir: str = "models"):
        """
        Initialize model manager.
        
        Args:
            models_dir: Directory to store models
        """
        if self._initialized:
            return
        
        self.models_dir = models_dir
        self._ensure_models_dir()
        self._initialized = True
        logger.info(f"ModelManager initialized with models_dir: {models_dir}")
    
    def _ensure_models_dir(self):
        """Ensure models directory exists."""
        os.makedirs(self.models_dir, exist_ok=True)
    
    def get_model(self, name: str) -> str:
        """
        Get model path, downloading if necessary.
        
        Args:
            name: Model name (e.g., 'base', 'tiny', 'small')
            
        Returns:
            Path to the model file
            
        Raises:
            ValueError: If model name is invalid
            RuntimeError: If download fails
        """
        if name not in self.MODELS:
            raise ValueError(
                f"Invalid model: {name}. Available: {', '.join(self.MODELS)}"
            )
        
        model_path = self.get_model_path(name)
        
        if not os.path.exists(model_path):
            logger.info(f"Model '{name}' not found locally, downloading...")
            self.download_model(name)
        
        return model_path
    
    def get_model_path(self, name: str) -> str:
        """
        Get the local path for a model.
        
        Args:
            name: Model name
            
        Returns:
            Path where model is/would be stored
        """
        filename = self.MODEL_FILENAMES.get(name, f"ggml-{name}.bin")
        return os.path.join(self.models_dir, filename)
    
    def model_exists(self, name: str) -> bool:
        """
        Check if a model is downloaded.
        
        Args:
            name: Model name
            
        Returns:
            True if model exists locally
        """
        return os.path.exists(self.get_model_path(name))
    
    def download_model(self, name: str, force: bool = False) -> str:
        """
        Download a model.
        
        Args:
            name: Model name to download
            force: If True, re-download even if exists
            
        Returns:
            Path to downloaded model
            
        Raises:
            ValueError: If model name is invalid
            RuntimeError: If download fails
        """
        if name not in self.MODELS:
            available = ", ".join(self.MODELS)
            raise ValueError(f"Invalid model: {name}. Available: {available}")
        
        model_path = self.get_model_path(name)
        
        if os.path.exists(model_path) and not force:
            logger.info(f"Model '{name}' already exists: {model_path}")
            return model_path
        
        # Determine source based on model type
        source = self.TDRZ_SOURCE if "tdrz" in name else self.DEFAULT_SOURCE
        url = f"{source}/resolve/main/ggml-{name}.bin"
        
        logger.info(f"Downloading model '{name}' from {source}...")
        
        try:
            self._download_file(url, model_path)
            logger.info(f"Model downloaded: {model_path}")
            return model_path
        except Exception as e:
            logger.error(f"Failed to download model '{name}': {e}")
            raise RuntimeError(f"Failed to download model: {e}")
    
    def _download_file(self, url: str, output_path: str):
        """
        Download a file with progress bar.
        
        Args:
            url: URL to download from
            output_path: Path to save file
        """
        filename = os.path.basename(output_path)
        
        with tqdm(
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            miniters=1,
            desc=filename,
        ) as pbar:
            def progress_hook(block_num, block_size, total_size):
                if pbar.total is None and total_size > 0:
                    pbar.total = total_size
                pbar.update(block_size)
            
            urllib.request.urlretrieve(url, output_path, reporthook=progress_hook)
    
    def list_available_models(self) -> list[str]:
        """
        List all available model names.
        
        Returns:
            List of model names that can be downloaded
        """
        return self.MODELS.copy()
    
    def list_downloaded_models(self) -> list[str]:
        """
        List models that are downloaded locally.
        
        Returns:
            List of downloaded model names
        """
        downloaded = []
        for name in self.MODELS:
            if self.model_exists(name):
                downloaded.append(name)
        return downloaded
    
    def get_model_size(self, name: str) -> int:
        """
        Get size of a downloaded model.
        
        Args:
            name: Model name
            
        Returns:
            Size in bytes, or -1 if not downloaded
        """
        model_path = self.get_model_path(name)
        if os.path.exists(model_path):
            return os.path.getsize(model_path)
        return -1
    
    def delete_model(self, name: str) -> bool:
        """
        Delete a downloaded model.
        
        Args:
            name: Model name to delete
            
        Returns:
            True if deleted, False if not found
        """
        model_path = self.get_model_path(name)
        if os.path.exists(model_path):
            os.remove(model_path)
            logger.info(f"Deleted model: {name}")
            return True
        return False
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None
