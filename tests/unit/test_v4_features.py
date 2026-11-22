"""Comprehensive unit tests for v4.0.0 features."""

from __future__ import annotations

import json
import stat
from unittest.mock import MagicMock, patch

import pytest

from subtitle_generator.cli.commands import main
from subtitle_generator.core.backends import create_transcriber
from subtitle_generator.core.transcriber import WhisperCppTranscriber
from subtitle_generator.core.video_processor import escape_ffmpeg_filter_path
from subtitle_generator.core.watcher import FolderWatcher
from subtitle_generator.utils.config import get_config_default, load_config, write_default_config
from subtitle_generator.utils.doctor import format_diagnostics, run_diagnostics
from subtitle_generator.utils.downloader import is_yt_dlp_url
from subtitle_generator.utils.exceptions import TranscriptionError
from subtitle_generator.utils.formatters import (
    ASSFormatter,
    JSONFormatter,
    SubtitleFormatterFactory,
    SubtitleSegment,
    TTMLFormatter,
    WordTiming,
)
from subtitle_generator.utils.postprocess import (
    lint_segments,
    lint_subtitle_file,
    reflow_segments,
    scrub_hallucinations,
    shift_subtitle_file,
    wrap_lines_balanced,
)
from subtitle_generator.utils.translator import translate_segments
from subtitle_generator.utils.validators import parse_output_formats
from subtitle_generator.utils.whisper_setup import detect_platform_asset_name


def _make_executable(p, content="#!/bin/sh\nexit 0\n") -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


class TestNewFormatters:
    def test_ass_formatter_clean_and_karaoke(self):
        segs = [
            SubtitleSegment(
                index=1,
                start_time=1.0,
                end_time=3.0,
                text="Hello world",
                words=[
                    WordTiming("Hello", 1.0, 1.8),
                    WordTiming("world", 1.9, 3.0),
                ],
            )
        ]
        clean = ASSFormatter(style="clean").format(segs)
        assert "[Script Info]" in clean
        assert "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello world" in clean

        karaoke = ASSFormatter(style="karaoke").format(segs)
        assert "{\\kf80}Hello" in karaoke
        assert "{\\kf110}world" in karaoke

        parsed = ASSFormatter().parse(karaoke)
        assert len(parsed) == 1
        assert parsed[0].text == "Hello world"

    def test_ttml_roundtrip(self):
        segs = [
            SubtitleSegment(1, 0.5, 2.5, "Line one\nLine two"),
            SubtitleSegment(2, 3.0, 5.0, "Rock & Roll <Live>"),
        ]
        fmt = TTMLFormatter()
        xml_str = fmt.format(segs)
        assert "xmlns=\"http://www.w3.org/ns/ttml\"" in xml_str
        assert "&amp;" in xml_str
        parsed = fmt.parse(xml_str)
        assert len(parsed) == 2
        assert parsed[0].text == "Line one\nLine two"
        assert parsed[1].text == "Rock & Roll <Live>"

    def test_json_formatter_and_whisper_cpp_json_parse(self):
        whisper_json = json.dumps({
            "transcription": [
                {
                    "offsets": {"from": 1000, "to": 2500},
                    "text": " Hello world",
                    "tokens": [
                        {"text": " Hello", "offsets": {"from": 1000, "to": 1600}, "p": 0.95},
                        {"text": " world", "offsets": {"from": 1700, "to": 2500}, "p": 0.98},
                        {"text": "[_BEG_]", "offsets": {"from": 1000, "to": 1000}, "p": 1.0},
                    ],
                }
            ]
        })
        fmt = JSONFormatter()
        segs = fmt.parse(whisper_json)
        assert len(segs) == 1
        assert segs[0].text == "Hello world"
        assert len(segs[0].words) == 2
        assert segs[0].words[0].word == "Hello"

        re_encoded = fmt.format(segs)
        re_parsed = fmt.parse(re_encoded)
        assert len(re_parsed) == 1
        assert re_parsed[0].words[1].word == "world"

    def test_factory_registers_ass_ttml_json(self):
        assert isinstance(SubtitleFormatterFactory.create("ass"), ASSFormatter)
        assert isinstance(SubtitleFormatterFactory.create("ttml"), TTMLFormatter)
        assert isinstance(SubtitleFormatterFactory.create("json"), JSONFormatter)


class TestPostProcessAndQC:
    def test_scrub_hallucinations(self):
        segs = [
            SubtitleSegment(1, 0.0, 1.0, "[BLANK_AUDIO]"),
            SubtitleSegment(2, 1.0, 2.0, "Welcome back."),
            SubtitleSegment(3, 2.0, 3.0, "Thank you."),
            SubtitleSegment(4, 3.0, 4.0, "Thank you."),
            SubtitleSegment(5, 4.0, 5.0, "Thank you."),
            SubtitleSegment(6, 5.0, 6.0, "Thank you."),
        ]
        cleaned = scrub_hallucinations(segs)
        # Drops [BLANK_AUDIO] and 3rd/4th consecutive identical cues
        assert [s.text for s in cleaned] == ["Welcome back.", "Thank you.", "Thank you."]

    def test_wrap_lines_balanced(self):
        wrapped = wrap_lines_balanced("This is a moderately long sentence that needs two balanced lines.", max_cpl=42, max_lines=2)
        lines = wrapped.splitlines()
        assert len(lines) == 2
        assert all(len(line) <= 42 for line in lines)

    def test_reflow_netflix_and_lint_pass(self):
        long_text = (
            "This is a very long subtitle segment that clearly violates Netflix forty-two "
            "characters per line guidelines and should be cleanly split into compliant cues."
        )
        segs = [SubtitleSegment(1, 0.0, 10.0, long_text)]
        reflowed = reflow_segments(segs, preset_name="netflix")
        assert len(reflowed) >= 2
        report = lint_segments(reflowed, standard="netflix")
        assert report.passed is True

    def test_lint_detects_cpl_and_overlap(self, tmp_path):
        srt = tmp_path / "bad.srt"
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:03,000\n"
            + ("A" * 60)
            + "\n\n2\n00:00:02,000 --> 00:00:04,000\nOverlapping cue\n",
            encoding="utf-8",
        )
        report = lint_subtitle_file(str(srt), standard="netflix")
        assert report.passed is False
        codes = {i.code for i in report.issues}
        assert "MAX_CPL" in codes
        assert "OVERLAP" in codes

    def test_shift_subtitle_file(self, tmp_path):
        srt = tmp_path / "sync.srt"
        out = tmp_path / "shifted.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,500\nHello\n", encoding="utf-8")
        shift_subtitle_file(str(srt), offset_ms=500, output_path=str(out))
        text = out.read_text(encoding="utf-8")
        assert "00:00:01,500 --> 00:00:03,000" in text


class TestConfigDoctorAndCLI:
    def test_config_roundtrip(self, tmp_path):
        cfg_file = str(tmp_path / "config.toml")
        write_default_config(cfg_file)
        cfg = load_config(user_config_path=cfg_file, local_config_path=str(tmp_path / "none.toml"))
        assert get_config_default(cfg, "model", "tiny") == "base"
        assert get_config_default(cfg, "vad", False) is True
        assert get_config_default(cfg, "style", "box", section="burn") == "clean"

    def test_doctor_diagnostics_structure(self, tmp_path):
        report = run_diagnostics(models_dir=str(tmp_path))
        assert "platform" in report
        assert "gpu" in report
        assert "whisper_cli" in report
        assert "ffmpeg" in report
        rendered = format_diagnostics(report)
        assert "Environment Diagnostics" in rendered

    def test_parse_output_formats(self):
        fmts, err = parse_output_formats("srt, vtt, ass, srt")
        assert err is None
        assert fmts == ["srt", "vtt", "ass"]

        fmts2, err2 = parse_output_formats("srt,invalid")
        assert fmts2 == []
        assert err2 is not None

    def test_cli_lint_and_shift_and_config(self, tmp_path, capsys):
        srt = tmp_path / "ok.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nShort clean line.\n", encoding="utf-8")
        assert main(["lint", str(srt), "--standard", "netflix", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["passed"] is True

        shifted = tmp_path / "shifted.srt"
        assert main(["shift", str(srt), "--offset", "1000", "-o", str(shifted)]) == 0
        assert "00:00:01,000 --> 00:00:03,000" in shifted.read_text(encoding="utf-8")


class TestCrossPlatformHelpers:
    def test_escape_ffmpeg_filter_path_handles_special_chars(self):
        escaped = escape_ffmpeg_filter_path("/tmp/sub [1]/it's:test.srt")
        assert "\\[" in escaped
        assert "\\]" in escaped
        assert "\\'" in escaped
        assert "\\:" in escaped

    def test_yt_dlp_url_detection(self):
        assert is_yt_dlp_url("https://www.youtube.com/watch?v=abc") is True
        assert is_yt_dlp_url("https://youtu.be/abc") is True
        assert is_yt_dlp_url("https://vimeo.com/12345") is True
        assert is_yt_dlp_url("https://example.com/file.mp4") is False

    def test_detect_platform_asset_name(self):
        asset = detect_platform_asset_name()
        assert asset is None or asset.startswith("whisper-cli-")

    def test_unknown_backend_raises(self):
        with pytest.raises(TranscriptionError):
            create_transcriber(backend="nonexistent-backend")

    def test_folder_watcher_stability_check(self, tmp_path):
        in_dir = tmp_path / "watch_in"
        out_dir = tmp_path / "watch_out"
        in_dir.mkdir()

        watcher = FolderWatcher(str(in_dir), str(out_dir), poll_interval=0.2)
        new_vid = in_dir / "clip.mp4"
        new_vid.write_bytes(b"12345678")

        with patch.object(watcher, "_process_file", return_value=str(out_dir / "clip.vtt")) as mock_proc:
            # First poll records initial size (stability debounce)
            assert watcher.poll_once() == []
            assert mock_proc.call_count == 0
            # Second poll sees stable size and processes file
            assert watcher.poll_once() == [str(out_dir / "clip.vtt")]
            assert mock_proc.call_count == 1
            # Third poll ignores already processed file
            assert watcher.poll_once() == []
            assert mock_proc.call_count == 1

    def test_transcriber_live_progress_parsing_and_vad_flags(self, tmp_path):
        WhisperCppTranscriber._capabilities_cache.clear()
        WhisperCppTranscriber._vi_support_cache.clear()

        binary = _make_executable(tmp_path / "whisper-cli")
        vad_model = tmp_path / "ggml-silero-v5.1.2.bin"
        vad_model.write_bytes(b"vad")
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"RIFF....WAVE")

        t = WhisperCppTranscriber(binary_path=binary, vad=True, vad_model_path=str(vad_model))
        WhisperCppTranscriber._capabilities_cache[binary] = {
            "video_input": True,
            "vad": True,
            "progress": True,
            "dtw": True,
            "tinydiarize": True,
            "diarize": True,
            "json_full": True,
            "suppress_nst": True,
            "carry_initial_prompt": True,
        }
        WhisperCppTranscriber._vi_support_cache[binary] = True

        captured_argv = []
        progress_events = []

        class FakePopen:
            def __init__(self, argv, **kw):
                captured_argv.append(argv)
                self.stderr = iter([
                    "whisper_print_progress_callback: progress =  25%\n",
                    "whisper_print_progress_callback: progress =  80%\n",
                ])
                self.stdout = MagicMock()
                self.stdout.read.return_value = ""
                self.returncode = 0

            def wait(self, timeout=None):
                return 0

        with patch("subprocess.Popen", FakePopen):
            res = t.transcribe(
                input_path=str(audio),
                model_path=str(tmp_path / "ggml-base.bin"),
                output_formats=["srt", "vtt"],
                output_dir=str(tmp_path / "out"),
                progress_callback=lambda s, p: progress_events.append((s, p)),
            )

        assert res.success is True
        argv = captured_argv[0]
        assert "--vad" in argv
        assert "-vm" in argv
        assert "-pp" in argv
        assert "-osrt" in argv
        assert "-ovtt" in argv
        assert ("transcribing", 0.25) in progress_events
        assert ("transcribing", 0.8) in progress_events

    def test_translate_segments_preserves_timestamps(self):
        segs = [
            SubtitleSegment(1, 1.0, 3.0, "Hello"),
            SubtitleSegment(2, 4.0, 6.0, "Goodbye"),
        ]
        with patch(
            "subtitle_generator.utils.translator._translate_with_argos",
            return_value=["Hola", "Adiós"],
        ):
            translated = translate_segments(segs, target_lang="es", provider="argos")
        assert [s.text for s in translated] == ["Hola", "Adiós"]
        assert translated[0].start_time == 1.0
        assert translated[1].end_time == 6.0
