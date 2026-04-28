"""
Unit tests for subtitle_generator.utils.paths.

These tests exercise the binary-discovery and cache-dir resolution logic
that was added in 3.0.2 to fix the "pip-installed CLI cannot find
whisper-cli" bug. We use an isolated tmp dir for every test so they pass
on macOS, Linux, and Windows CI runners regardless of what the host
system actually has on PATH.
"""

import os
import stat
import sys
from unittest.mock import patch

import pytest

from subtitle_generator.utils import paths as paths_mod
from subtitle_generator.utils.paths import (
    ENV_DATA_DIR,
    ENV_MODELS_DIR,
    ENV_WHISPER_BINARY,
    default_data_dir,
    default_models_dir,
    default_output_dir,
    find_whisper_binary,
    installed_whisper_binary,
    installed_whisper_binary_target,
    whisper_binary_install_hint,
)


def _make_executable(p):
    """Create an empty file at ``p`` and mark it executable."""
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Strip all related env vars so tests don't leak each other's state."""
    monkeypatch.delenv(ENV_WHISPER_BINARY, raising=False)
    monkeypatch.delenv(ENV_MODELS_DIR, raising=False)
    monkeypatch.delenv(ENV_DATA_DIR, raising=False)


class TestFindWhisperBinary:
    def test_explicit_path_wins(self, tmp_path, monkeypatch):
        # Even if PATH and env var would resolve, an explicit argument
        # should be returned (assuming it's executable).
        binary = _make_executable(tmp_path / "explicit-whisper")
        monkeypatch.setenv(ENV_WHISPER_BINARY, "/nonexistent")
        with patch.object(paths_mod.shutil, "which", return_value="/nonexistent/path"):
            assert find_whisper_binary(binary) == os.path.abspath(binary)

    def test_explicit_path_invalid_falls_through_to_env(self, tmp_path, monkeypatch):
        env_binary = _make_executable(tmp_path / "env-whisper")
        monkeypatch.setenv(ENV_WHISPER_BINARY, str(env_binary))
        # Explicit path doesn't exist; we fall through to the env var.
        with patch.object(paths_mod.shutil, "which", return_value=None):
            assert find_whisper_binary("/nonexistent/binary") == str(env_binary)

    def test_env_var_resolves(self, tmp_path, monkeypatch):
        env_binary = _make_executable(tmp_path / "whisper-from-env")
        monkeypatch.setenv(ENV_WHISPER_BINARY, str(env_binary))
        with patch.object(paths_mod.shutil, "which", return_value=None):
            assert find_whisper_binary() == str(env_binary)

    def test_path_lookup_resolves(self, tmp_path, monkeypatch):
        path_binary = _make_executable(tmp_path / "whisper-cli")
        # No env, no explicit. PATH lookup is the only signal.
        monkeypatch.chdir(tmp_path)  # avoid hitting legacy ./binary fallback

        def fake_which(name):
            return str(path_binary) if name == "whisper-cli" else None

        with patch.object(paths_mod.shutil, "which", side_effect=fake_which):
            assert find_whisper_binary() == os.path.abspath(str(path_binary))

    def test_legacy_checkout_layout(self, tmp_path, monkeypatch):
        # Mimic this project's setup_whisper.sh layout: ./binary/whisper-cli
        # relative to the current working directory.
        binary_dir = tmp_path / "binary"
        binary_dir.mkdir()
        legacy = _make_executable(binary_dir / "whisper-cli")
        monkeypatch.chdir(tmp_path)

        with patch.object(paths_mod.shutil, "which", return_value=None):
            assert find_whisper_binary() == legacy

    def test_user_data_install_beats_path(self, tmp_path, monkeypatch):
        # Once `subtitle setup-whisper` runs, its binary in the user-data
        # dir must win over an incompatible `whisper-cli` on PATH (e.g.
        # Homebrew's 1.8.4). Otherwise users hit silent-no-output bugs.
        installed = _make_executable(tmp_path / "data-install")
        monkeypatch.chdir(tmp_path)
        with patch.object(
            paths_mod, "installed_whisper_binary", return_value=installed
        ), patch.object(
            paths_mod.shutil, "which", return_value="/some/system/whisper-cli"
        ):
            assert find_whisper_binary() == installed

    def test_returns_none_when_nothing_found(self, tmp_path, monkeypatch):
        # Empty CWD, no env, no PATH match -> None (caller must show the
        # install hint).
        monkeypatch.chdir(tmp_path)
        with patch.object(paths_mod.shutil, "which", return_value=None):
            assert find_whisper_binary() is None

    def test_invalid_env_var_falls_through(self, tmp_path, monkeypatch):
        # If SUBTITLE_WHISPER_BINARY points somewhere that doesn't exist,
        # we should warn (logged) and continue resolution rather than
        # silently returning the broken path.
        path_binary = _make_executable(tmp_path / "whisper-cli")
        monkeypatch.setenv(ENV_WHISPER_BINARY, str(tmp_path / "does-not-exist"))
        monkeypatch.chdir(tmp_path / "..")

        def fake_which(name):
            return str(path_binary) if name == "whisper-cli" else None

        with patch.object(paths_mod.shutil, "which", side_effect=fake_which):
            assert find_whisper_binary() == os.path.abspath(str(path_binary))


class TestWhisperBinaryInstallHint:
    def test_leads_with_setup_whisper(self):
        # The hint is the user's first signal when something is wrong.
        # `subtitle setup-whisper` fixes 99% of cases in one command, so
        # it must appear first and prominently.
        hint = whisper_binary_install_hint()
        assert "subtitle setup-whisper" in hint
        first_line_after_intro = hint.split("\n", 2)[1].lower()
        assert "setup-whisper" in first_line_after_intro

    def test_includes_override_options(self):
        hint = whisper_binary_install_hint()
        assert ENV_WHISPER_BINARY in hint
        assert "--whisper-binary" in hint

    def test_macos_mentions_xcode_and_cmake(self):
        with patch.object(paths_mod.sys, "platform", "darwin"):
            hint = whisper_binary_install_hint()
        assert "xcode-select" in hint
        assert "cmake" in hint

    def test_linux_mentions_build_essential(self):
        with patch.object(paths_mod.sys, "platform", "linux"):
            hint = whisper_binary_install_hint()
        assert "build-essential" in hint
        assert "cmake" in hint

    def test_windows_mentions_build_tools(self):
        with patch.object(paths_mod.sys, "platform", "win32"):
            hint = whisper_binary_install_hint()
        assert "Visual Studio" in hint or "Build Tools" in hint


def _normalise(path: str) -> str:
    """Normalise path separators so cross-OS substring/endswith assertions
    behave the same on Linux/macOS and Windows runners.

    These tests mock ``sys.platform`` to exercise each branch, but the
    underlying ``os.path.join`` / ``os.path.expanduser`` calls still use
    the *host* separator, so on a Windows runner mocking ``darwin`` yields
    a path with mixed slashes. We compare on the POSIX form to keep the
    branching logic — not the formatting — under test.
    """
    return path.replace(os.sep, "/")


class TestDefaultModelsDir:
    def test_env_var_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_MODELS_DIR, str(tmp_path / "custom-models"))
        assert default_models_dir() == os.path.abspath(
            str(tmp_path / "custom-models")
        )

    def test_macos_default(self, monkeypatch):
        monkeypatch.delenv(ENV_MODELS_DIR, raising=False)
        with patch.object(paths_mod.sys, "platform", "darwin"):
            result = default_models_dir()
        assert _normalise(result).endswith(
            "Library/Caches/subtitle-generator/models"
        )

    def test_linux_xdg(self, monkeypatch, tmp_path):
        monkeypatch.delenv(ENV_MODELS_DIR, raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        with patch.object(paths_mod.sys, "platform", "linux"):
            result = default_models_dir()
        # tmp_path uses host separators; compare via normalised form.
        expected = _normalise(str(tmp_path / "subtitle-generator" / "models"))
        assert _normalise(result) == expected

    def test_linux_default_no_xdg(self, monkeypatch):
        monkeypatch.delenv(ENV_MODELS_DIR, raising=False)
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        with patch.object(paths_mod.sys, "platform", "linux"):
            result = default_models_dir()
        assert _normalise(result).endswith(
            ".cache/subtitle-generator/models"
        )

    def test_windows_localappdata(self, monkeypatch, tmp_path):
        monkeypatch.delenv(ENV_MODELS_DIR, raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        with patch.object(paths_mod.sys, "platform", "win32"):
            result = default_models_dir()
        expected = _normalise(
            str(tmp_path / "subtitle-generator" / "Cache" / "models")
        )
        assert _normalise(result) == expected


class TestDefaultOutputDir:
    def test_under_tempdir(self):
        import tempfile

        d = default_output_dir()
        assert d.startswith(tempfile.gettempdir())
        assert d.endswith("subtitle-generator")


class TestDefaultDataDir:
    def test_env_var_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "custom-data"))
        assert default_data_dir() == os.path.abspath(
            str(tmp_path / "custom-data")
        )

    def test_macos_default_is_application_support(self, monkeypatch):
        with patch.object(paths_mod.sys, "platform", "darwin"):
            result = default_data_dir()
        assert _normalise(result).endswith(
            "Library/Application Support/subtitle-generator"
        )

    def test_linux_xdg_data_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        with patch.object(paths_mod.sys, "platform", "linux"):
            result = default_data_dir()
        assert _normalise(result) == _normalise(
            str(tmp_path / "subtitle-generator")
        )

    def test_linux_default_no_xdg(self, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        with patch.object(paths_mod.sys, "platform", "linux"):
            result = default_data_dir()
        assert _normalise(result).endswith(
            ".local/share/subtitle-generator"
        )

    def test_windows_localappdata(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        with patch.object(paths_mod.sys, "platform", "win32"):
            result = default_data_dir()
        assert _normalise(result) == _normalise(
            str(tmp_path / "subtitle-generator")
        )


class TestInstalledWhisperBinary:
    def test_returns_none_when_absent(self, tmp_path, monkeypatch):
        # Point data dir at an empty directory; nothing installed yet.
        monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
        assert installed_whisper_binary() is None

    def test_returns_path_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        binary = _make_executable(bin_dir / "whisper-cli")
        assert installed_whisper_binary() == binary

    def test_target_is_under_data_dir_bin(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
        target = installed_whisper_binary_target()
        # Target sits at <data_dir>/bin/whisper-cli{.exe}
        normalised = _normalise(target)
        assert normalised.startswith(_normalise(str(tmp_path)))
        assert "/bin/whisper-cli" in normalised
