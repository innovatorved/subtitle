"""Tests for the setup-whisper build pipeline (subprocess calls mocked)."""

import os
import stat
import sys
from unittest.mock import patch, MagicMock

import pytest

from subtitle_generator.utils import paths as paths_mod
from subtitle_generator.utils import whisper_setup as ws


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Pin the data dir to a tmp dir for every test."""
    monkeypatch.setenv("SUBTITLE_DATA_DIR", str(tmp_path))
    yield


def _make_executable(p) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


class TestDependencyChecks:
    def test_missing_git_raises(self, monkeypatch):
        # `shutil.which` returning None for git should produce a clear
        # WhisperSetupError instead of letting subprocess fail later.
        def fake_which(name):
            return None if name == "git" else f"/usr/bin/{name}"

        with patch.object(ws.shutil, "which", side_effect=fake_which):
            with pytest.raises(ws.WhisperSetupError) as exc:
                ws.setup_whisper()
        assert "git" in str(exc.value).lower()

    def test_missing_cmake_raises(self):
        def fake_which(name):
            return None if name == "cmake" else f"/usr/bin/{name}"

        with patch.object(ws.shutil, "which", side_effect=fake_which):
            with pytest.raises(ws.WhisperSetupError) as exc:
                ws.setup_whisper()
        assert "cmake" in str(exc.value).lower()

    def test_missing_compiler_raises(self):
        # All build tools present, no C++ compiler at all.
        def fake_which(name):
            if name in ("c++", "g++", "clang++", "cl"):
                return None
            return f"/usr/bin/{name}"

        with patch.object(ws.shutil, "which", side_effect=fake_which):
            with pytest.raises(ws.WhisperSetupError) as exc:
                ws.setup_whisper()
        assert "compiler" in str(exc.value).lower()


class TestArgvBuilding:
    """Verify the subprocess argvs we hand off match expectations."""

    def _all_present(self, monkeypatch):
        # Pretend every tool is on PATH so the dependency gate passes.
        monkeypatch.setattr(
            ws.shutil,
            "which",
            lambda name: f"/usr/bin/{name}",
        )

    def test_fresh_clone_uses_depth_1_branch(self, tmp_path, monkeypatch):
        self._all_present(monkeypatch)
        runs = []

        def fake_run(argv, **kw):
            runs.append((argv, kw))
            # Fabricate a built binary at the canonical CMake output path
            # so the locate-step succeeds.
            if argv[:2] == ["/usr/bin/cmake", "--build"]:
                build_dir = next(
                    a for a in argv if "build" in a and os.path.basename(a) == "build"
                )
                _make_executable(
                    tmp_path / "whisper.cpp" / "build" / "bin" / "whisper-cli"
                )
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        with patch.object(ws.subprocess, "run", side_effect=fake_run):
            result = ws.setup_whisper(repo_url="https://example.com/foo.git",
                                      ref="main")

        # First invocation must be the shallow clone with the requested ref.
        clone_argv = runs[0][0]
        assert clone_argv[0].endswith("git")
        assert "clone" in clone_argv
        assert "--depth" in clone_argv
        assert "1" in clone_argv
        assert "--branch" in clone_argv
        assert "main" in clone_argv
        assert "https://example.com/foo.git" in clone_argv

        # Some later invocation must be the cmake configure step with
        # the project's build flags.
        configure = next(
            a for (a, _) in runs
            if a[:1] == ["/usr/bin/cmake"] and "-B" in a and "--build" not in a
        )
        assert "-DCMAKE_BUILD_TYPE=Release" in configure
        assert "-DWHISPER_BUILD_EXAMPLES=ON" in configure

        # The smoke test (`-h`) runs against the installed file, not the
        # build dir, so the user can't get a successful return on a
        # non-functional binary.
        assert any(
            a[0] == result.binary_path and a[1] == "-h"
            for (a, _) in runs
        )

    def test_force_wipes_existing_checkout(self, tmp_path, monkeypatch):
        self._all_present(monkeypatch)
        # Pre-create a fake existing checkout with a marker file.
        src_dir = tmp_path / "whisper.cpp"
        (src_dir / ".git").mkdir(parents=True)
        marker = src_dir / "should-be-deleted"
        marker.write_text("old")

        def fake_run(argv, **kw):
            if argv[:2] == ["/usr/bin/cmake", "--build"]:
                _make_executable(
                    tmp_path / "whisper.cpp" / "build" / "bin" / "whisper-cli"
                )
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        with patch.object(ws.subprocess, "run", side_effect=fake_run):
            ws.setup_whisper(force=True)

        # `--force` must wipe the existing tree before re-cloning.
        assert not marker.exists()


class TestLocateBuiltBinary:
    def test_picks_cmake_release_on_windows(self, tmp_path, monkeypatch):
        # Simulate MSBuild's multi-config output layout.
        monkeypatch.setattr(
            ws.shutil, "which", lambda name: f"/usr/bin/{name}"
        )

        def fake_run(argv, **kw):
            if argv[:2] == ["/usr/bin/cmake", "--build"]:
                _make_executable(
                    tmp_path / "whisper.cpp" / "build" / "bin"
                    / "Release" / "whisper-cli.exe"
                )
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        with patch.object(ws.subprocess, "run", side_effect=fake_run), \
             patch.object(ws.sys, "platform", "win32"):
            result = ws.setup_whisper()

        # Even though sys.platform is mocked to win32, the file
        # extension follows that mock via installed_whisper_binary_target.
        assert result.binary_path.endswith("whisper-cli.exe")
