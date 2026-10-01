"""Focused checks for graceful reload and explicit saved-Set reopening."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "AbletonMCP_Remote_Script"))

import ableton_install as inst
import launch_ableton as launcher
from mixins.session import SessionMixin


def test_session_reports_saved_set_path():
    mixer = SimpleNamespace(volume=SimpleNamespace(value=0.85), panning=SimpleNamespace(value=0))
    harness = SessionMixin()
    harness._song = SimpleNamespace(
        tempo=138, signature_numerator=4, signature_denominator=4,
        tracks=[], return_tracks=[], master_track=SimpleNamespace(mixer_device=mixer),
        file_path="C:/sets/Psy AI Test 2 Live 12.4.als",
    )
    assert harness._get_session_info()["file_path"] == harness._song.file_path


def test_graceful_quit_never_force_kills_on_timeout(monkeypatch):
    procs = [{"pid": "123", "name": "Ableton Live 12 Suite.exe"}]
    monkeypatch.setattr(inst, "running_live_processes", lambda **kw: procs)
    close = Mock(return_value=1)
    monkeypatch.setattr(inst, "_post_close_to_live_windows", close)
    run = Mock()
    monkeypatch.setattr(inst.subprocess, "run", run)

    with pytest.raises(RuntimeError, match="normal shutdown"):
        inst.quit_live(system="Windows", timeout=0)

    close.assert_called_once_with(pids=["123"])
    run.assert_not_called()


def test_start_live_passes_set_path_as_one_argument(tmp_path, monkeypatch):
    set_file = tmp_path / "Psy AI Test 2 Live 12.4.als"
    set_file.write_bytes(b"test")
    exe = tmp_path / "Ableton Live 12 Suite.exe"
    popen = Mock()
    monkeypatch.setattr(inst.subprocess, "Popen", popen)

    assert inst.start_live(exe, system="Windows", set_file=set_file) == exe
    assert popen.call_args.args[0] == [str(exe), str(set_file.resolve())]


def test_missing_set_is_rejected_before_quitting(tmp_path, monkeypatch):
    quit_live = Mock()
    monkeypatch.setattr(inst, "quit_live", quit_live)
    assert launcher.main(["--reload", "--set", str(tmp_path / "missing.als"), "--json"]) == 1
    quit_live.assert_not_called()


def test_wait_for_remote_script_ignores_startup_template(tmp_path, monkeypatch):
    set_file = tmp_path / "Psy AI Test 2 Live 12.4.als"
    responses = iter([
        {"tempo": 120, "file_path": str(tmp_path / "Do_Not_Save.als")},
        {"tempo": 138, "file_path": str(set_file)},
    ])
    monkeypatch.setattr(inst, "ping_remote_script", lambda **kw: next(responses))
    monkeypatch.setattr(inst.time, "sleep", lambda delay: None)

    result = inst.wait_for_remote_script(timeout=1, set_file=set_file)
    assert result["tempo"] == 138
