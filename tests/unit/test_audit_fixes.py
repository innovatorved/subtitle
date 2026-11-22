"""Unit tests covering audit fixes across formatters, video processor, batch, downloader, and CLI."""

import stat
from unittest.mock import MagicMock, patch

import pytest

from subtitle_generator.cli.commands import create_batch_parser, create_main_parser, main
from subtitle_generator.core.batch_processor import BatchProcessor, BatchState
from subtitle_generator.core.transcriber import WhisperCppTranscriber
from subtitle_generator.core.video_processor import VideoProcessor
from subtitle_generator.utils.downloader import download_file, is_google_drive_url, is_url
from subtitle_generator.utils.exceptions import DownloadError
from subtitle_generator.utils.formatters import (
    SRTFormatter,
    TXTFormatter,
    VTTFormatter,
)


def _make_executable(p, content="#!/bin/sh\nexit 0\n") -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


class TestFormatterFixes:
    def test_vtt_timestamp_rounding_boundary(self):
        fmt = VTTFormatter()
        assert fmt._format_timestamp(59.9999) == "00:01:00.000"
        assert fmt._format_timestamp(3599.9999) == "01:00:00.000"
        assert fmt._format_timestamp(-1.0) == "00:00:00.000"

    def test_vtt_parse_short_timestamps_crlf_and_bom(self):
        fmt = VTTFormatter()
        content = "\ufeffWEBVTT\r\n\r\n01:02.500 --> 01:05.750\r\nHello world\r\n"
        segments = fmt.parse(content)
        assert len(segments) == 1
        assert abs(segments[0].start_time - 62.5) < 1e-6
        assert abs(segments[0].end_time - 65.75) < 1e-6
        assert segments[0].text == "Hello world"

    def test_srt_parse_crlf_and_bom(self):
        fmt = SRTFormatter()
        content = "\ufeff1\r\n00:00:01,000 --> 00:00:03,500\r\nLine one\r\nLine two\r\n\r\n2\r\n00:00:04,000 --> 00:00:05,000\r\nSecond\r\n"
        segments = fmt.parse(content)
        assert len(segments) == 2
        assert segments[0].text == "Line one\nLine two"
        assert segments[1].text == "Second"

    def test_txt_format_empty(self):
        fmt = TXTFormatter()
        assert fmt.format([]) == ""


class TestVideoProcessorBurnFixes:
    def test_burn_subtitles_preserves_audio_stream(self, tmp_path):
        video = tmp_path / "clip.mp4"
        sub = tmp_path / "clip.srt"
        out = tmp_path / "clip_burned.mp4"
        video.write_bytes(b"00")
        sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")

        vp = VideoProcessor()
        captured_args = []

        def fake_run(args, **kw):
            captured_args.append(args)

        with patch.object(vp, "_run_ffmpeg", side_effect=fake_run), \
             patch.object(vp, "_detect_hw_encoder", return_value=None), \
             patch.object(vp, "get_video_info", return_value={"duration": 1.0, "audio_codec": "aac"}):
            ok = vp.burn_subtitles(str(video), str(sub), str(out))

        assert ok is True
        args = captured_args[-1]
        assert "-c:a" in args
        assert args[args.index("-c:a") + 1] == "copy"
        assert args[-1] == str(out)

    def test_burn_subtitles_handles_silent_video(self, tmp_path):
        video = tmp_path / "silent.mp4"
        sub = tmp_path / "silent.srt"
        out = tmp_path / "silent_burned.mp4"
        video.write_bytes(b"00")
        sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")

        vp = VideoProcessor()
        captured_args = []

        def fake_run(args, **kw):
            captured_args.append(args)

        with patch.object(vp, "_run_ffmpeg", side_effect=fake_run), \
             patch.object(vp, "_detect_hw_encoder", return_value=None), \
             patch.object(vp, "get_video_info", return_value={"duration": 1.0}):
            ok = vp.burn_subtitles(str(video), str(sub), str(out))

        assert ok is True
        args = captured_args[-1]
        assert "-c:a" not in args
        assert args[-1] == str(out)


class TestTranscriberAudioFallback:
    def setup_method(self):
        WhisperCppTranscriber._vi_support_cache.clear()

    def test_non_wav_audio_extracts_wav_when_binary_lacks_vi(self, tmp_path):
        binary = _make_executable(tmp_path / "stock-whisper-cli")
        audio_file = tmp_path / "podcast.m4a"
        audio_file.write_bytes(b"\x00" * 64)

        transcriber = WhisperCppTranscriber(binary_path=binary)
        captured = []

        def fake_run(argv, **kw):
            captured.append(argv)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = b"usage: whisper-cli [options] file0.wav\n" if "-h" in argv else b""
            mock.stderr = b""
            return mock

        def fake_extract(self_vp, video_path, output_path=None, audio_format="wav", sample_rate=16000):
            with open(output_path, "wb") as f:
                f.write(b"RIFF....WAVE")
            return output_path

        with patch("subprocess.run", side_effect=fake_run), \
             patch.object(VideoProcessor, "extract_audio", fake_extract):
            result = transcriber.transcribe(
                input_path=str(audio_file),
                model_path=str(tmp_path / "ggml-base.bin"),
                output_format="vtt",
                output_dir=str(tmp_path / "out"),
            )

        assert result.success is True
        argv = captured[-1]
        assert argv[argv.index("-f") + 1].endswith(".wav")


class TestBatchAndDownloaderFixes:
    def test_batch_normalizes_extensions_and_threads(self):
        bp = BatchProcessor(extensions=[" .MP4 ", " mkv", ""], threads=2, processors=2)
        assert bp.extensions == ["mp4", "mkv"]
        assert bp.threads == 2
        assert bp.processors == 2

    def test_batch_state_load_handles_bad_schema(self, tmp_path):
        bad_state = tmp_path / "bad_state.json"
        bad_state.write_text('{"unexpected_key": 123}', encoding="utf-8")
        assert BatchState.load(str(bad_state)) is None

    def test_url_and_gdrive_detection(self):
        assert is_url("https://example.com/video.mp4") is True
        assert is_url("http://example.com/audio.mp3") is True
        assert is_url("ftp://example.com/video.mp4") is False
        assert is_url("/local/path/video.mp4") is False
        assert is_google_drive_url("https://drive.google.com/file/d/abc/view") is True
        assert is_google_drive_url("https://example.com/video.mp4") is False

    def test_download_file_raises_download_error_on_failure(self, tmp_path):
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            with pytest.raises(DownloadError):
                download_file("https://example.com/video.mp4", output_path=str(tmp_path / "v.mp4"))


class TestCLIFixesExtra:
    def test_merge_and_burn_mutually_exclusive(self):
        parser = create_main_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["video.mp4", "--merge", "--burn"])
        assert exc.value.code == 2

    def test_batch_parser_accepts_threads_and_processors(self):
        parser = create_batch_parser()
        args = parser.parse_args(["--input-dir", "./videos", "--threads", "2", "--processors", "2"])
        assert args.threads == 2
        assert args.processors == 2

    def test_formats_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["formats", "--help"])
        assert exc.value.code == 0
        assert "subtitle formats" in capsys.readouterr().out
