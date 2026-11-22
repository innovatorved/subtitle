"""Folder watcher for automated subtitle pipelines (``subtitle watch``)."""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, Optional

from ..utils.exceptions import SubtitleError
from ..utils.file_handler import (
    directory_exists,
    ensure_directory,
    get_file_basename,
    list_files_with_extension,
)
from ..utils.validators import MEDIA_EXTENSIONS

logger = logging.getLogger(__name__)


class FolderWatcher:
    """Watches a directory for new media files and automatically generates subtitles.

    Uses a file-size stability check so partially written/copied files are
    never processed before writing finishes.
    """

    def __init__(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        model: str = "base",
        output_format: str = "vtt",
        poll_interval: float = 2.0,
        extensions: Optional[list[str]] = None,
        recursive: bool = False,
        whisper_binary: Optional[str] = None,
        models_dir: Optional[str] = None,
        language: Optional[str] = None,
        translate: bool = False,
        preset: Optional[str] = None,
        vad: bool = True,
        backend: str = "whisper.cpp",
        process_existing: bool = False,
    ):
        if not directory_exists(input_dir):
            raise SubtitleError(f"Watch directory does not exist: {input_dir}")

        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir) if output_dir else self.input_dir
        ensure_directory(self.output_dir)
        self.model = model
        self.output_format = output_format
        self.poll_interval = max(0.2, poll_interval)
        self.extensions = (
            [e.strip().lstrip(".").lower() for e in extensions if e.strip()]
            if extensions
            else sorted(MEDIA_EXTENSIONS)
        )
        self.recursive = recursive
        self.whisper_binary = whisper_binary
        self.models_dir = models_dir
        self.language = language
        self.translate = translate
        self.preset = preset
        self.vad = vad
        self.backend = backend
        self._seen_sizes: dict[str, int] = {}
        self._processed: set[str] = set()

        if not process_existing:
            for f in self._scan():
                self._processed.add(f)

    def _scan(self) -> list[str]:
        found: list[str] = []
        for ext in self.extensions:
            found.extend(list_files_with_extension(self.input_dir, ext, recursive=self.recursive))
        return sorted(set(found))

    def poll_once(
        self,
        on_event: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ) -> list[str]:
        """Run a single poll cycle and return newly generated subtitle paths."""
        generated: list[str] = []
        for path in self._scan():
            if path in self._processed:
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            # Require two consecutive polls with identical non-zero size
            prev = self._seen_sizes.get(path)
            if prev is None or prev != size or size == 0:
                self._seen_sizes[path] = size
                continue

            self._processed.add(path)
            self._seen_sizes.pop(path, None)
            if on_event:
                on_event("processing", path, None)

            out_path = self._process_file(path)
            if out_path:
                generated.append(out_path)
                if on_event:
                    on_event("complete", path, out_path)
            else:
                if on_event:
                    on_event("error", path, None)
        return generated

    def _process_file(self, file_path: str) -> Optional[str]:
        from ..models import ModelManager
        from ..utils.paths import default_output_dir
        from .backends import create_transcriber
        from .subtitle_gen import SubtitleGenerator

        try:
            transcriber = create_transcriber(
                backend=self.backend,
                binary_path=self.whisper_binary,
                language=self.language,
                translate=self.translate,
                vad=self.vad,
            )
            generator = SubtitleGenerator(transcriber, ModelManager(models_dir=self.models_dir))
            base_name = get_file_basename(file_path)
            final_output = os.path.join(self.output_dir, f"{base_name}.{self.output_format}")
            out, ok = generator.generate_and_rename(
                input_path=file_path,
                model_name=self.model,
                output_format=self.output_format,
                output_dir=default_output_dir(),
                output_path=final_output,
                language=self.language,
                translate=self.translate,
                vad=self.vad,
                preset=self.preset,
            )
            return out if ok else None
        except Exception as e:
            logger.error("Watcher failed on %s: %s", file_path, e)
            return None

    def run(
        self,
        max_cycles: Optional[int] = None,
        on_event: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ) -> None:
        """Continuously watch until KeyboardInterrupt or ``max_cycles`` reached."""
        cycles = 0
        while True:
            self.poll_once(on_event=on_event)
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(self.poll_interval)
