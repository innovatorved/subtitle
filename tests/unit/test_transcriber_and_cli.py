"""Unit tests for WhisperCppTranscriber, VideoProcessor, and CLI features."""

import os
import stat
from unittest.mock import MagicMock, patch

import pytest

from subtitle_generator.cli.commands import SubtitleCLI, SilentProgressObserver, main
from subtitle_generator.core.transcriber import WhisperCppTranscriber
from subtitle_generator.core.video_processor import VideoProcessor, _parse_frame_rate
from subtitle_generator.models.model_manager import ModelManager


def _make_executable(p, content="#!/bin/sh\nexit 0\n") -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


class TestWhisperCppTranscriberFeatures:
    def setup_method(self):
        WhisperCppTranscriber._vi_support_cache.clear()

    def test_language_and_translate_flags_in_argv(self, tmp_path):
        binary = _make_executable(tmp_path / "whisper-cli")
        transcriber = WhisperCppTranscriber(
            binary_path=binary,
            threads=6,
            processors=2,
            language="es",
            translate=True,
        )

        captured_argvs = []

        def fake_run(argv, **kw):
            captured_argvs.append(argv)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = b"options: -vi --video-input"
            mock.stderr = b""
            return mock

        with patch("subprocess.run", side_effect=fake_run):
            result = transcriber.transcribe(
                input_path=str(tmp_path / "clip.mp4"),
                model_path=str(tmp_path / "ggml-base.bin"),
                output_format="csv",
                output_dir=str(tmp_path / "out"),
            )

        assert result.success is True
        assert result.format == "csv"
        transcribe_argv = captured_argvs[-1]
        assert "-vi" in transcribe_argv
        assert "-l" in transcribe_argv
        assert transcribe_argv[transcribe_argv.index("-l") + 1] == "es"
        assert "-tr" in transcribe_argv
        assert "-ocsv" in transcribe_argv

    def test_fallback_to_wav_when_binary_lacks_vi(self, tmp_path):
        binary = _make_executable(tmp_path / "stock-whisper-cli")
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"\x00" * 64)

        transcriber = WhisperCppTranscriber(binary_path=binary)
        captured_argvs = []

        def fake_run(argv, **kw):
            captured_argvs.append(argv)
            mock = MagicMock()
            mock.returncode = 0
            # Simulate stock whisper-cli help output without -vi
            if "-h" in argv:
                mock.stdout = b"usage: whisper-cli [options] file0.wav\n  -f FNAME\n"
            else:
                mock.stdout = b""
            mock.stderr = b""
            return mock

        def fake_extract_audio(self_vp, video_path, output_path=None, audio_format="wav", sample_rate=16000):
            with open(output_path, "wb") as f:
                f.write(b"RIFF....WAVE")
            return output_path

        with patch("subprocess.run", side_effect=fake_run), \
             patch.object(VideoProcessor, "extract_audio", fake_extract_audio):
            result = transcriber.transcribe(
                input_path=str(video_file),
                model_path=str(tmp_path / "ggml-base.bin"),
                output_format="srt",
                output_dir=str(tmp_path / "out"),
            )

        assert result.success is True
        transcribe_argv = captured_argvs[-1]
        assert "-vi" not in transcribe_argv
        f_idx = transcribe_argv.index("-f")
        passed_input = transcribe_argv[f_idx + 1]
        assert passed_input.endswith(".wav")
        # Temporary WAV must be cleaned up in finally block
        assert not os.path.exists(passed_input)


class TestVideoProcessorFixes:
    def test_parse_frame_rate_safe(self):
        assert abs(_parse_frame_rate("30000/1001") - 29.97002997) < 1e-5
        assert _parse_frame_rate("25/1") == 25.0
        assert _parse_frame_rate("0/0") == 0.0
        assert _parse_frame_rate("0/1") == 0.0
        assert _parse_frame_rate(None) == 0.0
        assert _parse_frame_rate("invalid") == 0.0

    def test_merge_subtitles_auto_selects_container_codec(self, tmp_path):
        video = tmp_path / "in.mkv"
        sub = tmp_path / "in.srt"
        out_mkv = tmp_path / "out.mkv"
        out_webm = tmp_path / "out.webm"
        video.write_bytes(b"00")
        sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")

        vp = VideoProcessor()
        with patch("ffmpeg.input") as mock_in, \
             patch("ffmpeg.output") as mock_out, \
             patch("ffmpeg.run"):
            vp.merge_subtitles(str(video), str(sub), str(out_mkv))
            assert mock_out.call_args.kwargs["scodec"] == "srt"

            vp.merge_subtitles(str(video), str(sub), str(out_webm))
            assert mock_out.call_args.kwargs["scodec"] == "webvtt"


class TestCLIFixes:
    def setup_method(self):
        ModelManager.reset_instance()

    def teardown_method(self):
        ModelManager.reset_instance()

    def test_input_file_with_spaces_is_not_renamed_or_moved(self, tmp_path):
        spaced_dir = tmp_path / "My Videos"
        spaced_dir.mkdir(parents=True)
        spaced_video = spaced_dir / "my clip.mp4"
        spaced_video.write_bytes(b"\x00" * 128)

        binary = _make_executable(tmp_path / "whisper-cli")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "ggml-base.bin").write_bytes(b"model")

        out_dir = tmp_path / "out"
        observer = SilentProgressObserver()
        cli = SubtitleCLI(
            observer=observer,
            models_dir=str(models_dir),
            whisper_binary=binary,
        )

        def fake_transcribe(self_t, input_path, model_path, output_format="vtt", output_dir="data", **kw):
            os.makedirs(output_dir, exist_ok=True)
            out_file = os.path.join(output_dir, f"fake.{output_format}")
            with open(out_file, "w") as f:
                f.write("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello\n")
            from subtitle_generator.core.transcriber import TranscriptionResult
            return TranscriptionResult(
                process_id="fake",
                input_path=input_path,
                output_path=out_file,
                format=output_format,
                success=True,
            )

        from subtitle_generator.cli.commands import create_main_parser
        parser = create_main_parser()
        parsed = parser.parse_args([
            str(spaced_video),
            "--output-dir", str(out_dir),
            "--language", "en",
        ])
        parsed.command = None

        with patch.object(WhisperCppTranscriber, "transcribe", fake_transcribe):
            rc = cli.run(parsed)

        assert rc == 0
        # Original file with spaces in directory and filename MUST remain untouched!
        assert spaced_video.exists()
        assert (out_dir / "my clip.vtt").exists()

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "3.1.0" in captured.out
