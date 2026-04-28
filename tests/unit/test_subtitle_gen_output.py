"""Tests for SubtitleGenerator.generate_and_rename output routing."""

import os
from unittest.mock import MagicMock

import pytest

from subtitle_generator.core.subtitle_gen import SubtitleGenerator
from subtitle_generator.core.transcriber import (
    TranscriberStrategy,
    TranscriptionResult,
)


class _FakeTranscriber(TranscriberStrategy):
    """Drop-in transcriber that just writes a static file."""

    def __init__(self, raw_output_path: str, content: str = "1\nHELLO\n"):
        self._raw_output_path = raw_output_path
        self._content = content

    def transcribe(self, input_path, model_path, output_format="vtt",
                   output_dir="data", progress_callback=None):
        os.makedirs(os.path.dirname(self._raw_output_path), exist_ok=True)
        with open(self._raw_output_path, "w") as f:
            f.write(self._content)
        return TranscriptionResult(
            process_id="fake",
            input_path=input_path,
            output_path=self._raw_output_path,
            format=output_format,
            success=True,
        )

    def get_supported_formats(self):
        return ["vtt", "srt", "txt", "json", "lrc"]


def _make_input_video(path, byte_count=128):
    """Touch a file so file_exists() / validators pass."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * byte_count)
    return str(path)


@pytest.fixture
def model_manager_stub():
    """A trivial model_manager that returns a fixed path without I/O."""
    mgr = MagicMock()
    mgr.get_model.return_value = "/tmp/fake-model.bin"
    return mgr


class TestGenerateAndRenameOutputPath:
    def test_explicit_output_path_is_used(
        self, tmp_path, model_manager_stub
    ):
        # When the CLI hands us an explicit final destination (the new
        # 3.0.4 behaviour), the file must land *exactly* there — not
        # next to the input video.
        input_video = _make_input_video(tmp_path / "videos" / "story.mp4")
        raw = tmp_path / "transient" / "uuid-1234.srt"
        target = tmp_path / "user-cwd" / "story.srt"

        gen = SubtitleGenerator(
            transcriber=_FakeTranscriber(str(raw)),
            model_manager=model_manager_stub,
        )

        final, ok = gen.generate_and_rename(
            input_path=input_video,
            output_format="srt",
            output_dir=str(raw.parent),
            output_path=str(target),
        )

        assert ok is True
        assert final == str(target)
        assert target.is_file()
        # Source-side neighbour MUST NOT exist — that was the old bug.
        assert not (tmp_path / "videos" / "story.srt").exists()

    def test_default_routes_next_to_input_for_back_compat(
        self, tmp_path, model_manager_stub
    ):
        # When no explicit output_path is given, preserve the historic
        # API contract: rename next to the input file. Third-party
        # Python users may rely on this.
        input_video = _make_input_video(tmp_path / "videos" / "story.mp4")
        raw = tmp_path / "transient" / "uuid-5678.srt"

        gen = SubtitleGenerator(
            transcriber=_FakeTranscriber(str(raw)),
            model_manager=model_manager_stub,
        )

        final, ok = gen.generate_and_rename(
            input_path=input_video,
            output_format="srt",
            output_dir=str(raw.parent),
        )

        assert ok is True
        assert final == str(tmp_path / "videos" / "story.srt")

    def test_overwrites_existing_destination(
        self, tmp_path, model_manager_stub
    ):
        # A repeat run must replace stale output; without the explicit
        # remove + shutil.move the second `subtitle ...` call would
        # have raised on macOS/Linux.
        input_video = _make_input_video(tmp_path / "story.mp4")
        raw = tmp_path / "transient" / "uuid-1.srt"
        target = tmp_path / "out" / "story.srt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("STALE")

        gen = SubtitleGenerator(
            transcriber=_FakeTranscriber(str(raw), content="FRESH"),
            model_manager=model_manager_stub,
        )

        final, ok = gen.generate_and_rename(
            input_path=input_video,
            output_format="srt",
            output_dir=str(raw.parent),
            output_path=str(target),
        )

        assert ok is True
        assert target.read_text() == "FRESH"

    def test_target_directory_created_lazily(
        self, tmp_path, model_manager_stub
    ):
        # Users will pass --output-dir directories that don't exist yet.
        # The CLI also calls os.makedirs but we belt-and-brace inside
        # generate_and_rename so the Python API has the same guarantee.
        input_video = _make_input_video(tmp_path / "story.mp4")
        raw = tmp_path / "transient" / "uuid-2.srt"
        target = tmp_path / "deeply" / "nested" / "out" / "story.srt"

        gen = SubtitleGenerator(
            transcriber=_FakeTranscriber(str(raw)),
            model_manager=model_manager_stub,
        )

        final, ok = gen.generate_and_rename(
            input_path=input_video,
            output_format="srt",
            output_dir=str(raw.parent),
            output_path=str(target),
        )

        assert ok is True
        assert target.is_file()
