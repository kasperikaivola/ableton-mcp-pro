import json
import subprocess
import pytest

from MCP_Server.tools import midigenai as tool


def test_mcp_wrapper_forwards_generation_options(monkeypatch):
    captured = {}
    expected = {
        "prompt_tokens": 4,
        "generated_tokens": 8,
        "tempo_bpm": 128.0,
        "notes": [],
    }

    def fake_bridge(payload, timeout_seconds):
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return expected

    monkeypatch.setattr(tool, "_run_bridge_subprocess", fake_bridge)
    result = tool.generate_midi_continuation(
        None,
        notes=[{"pitch": 60, "start_time": 0, "duration": 1, "velocity": 100}],
        tempo_bpm=128,
        max_new_tokens=64,
        temperature=0.8,
        top_k=20,
        prompt_end_beat=4,
        pitch_range=[48, 84],
        version="v2",
        repo_id="example/model",
        timeout_seconds=45,
    )

    assert json.loads(result) == expected
    assert captured["payload"] == {
        "notes": [{"pitch": 60, "start_time": 0, "duration": 1, "velocity": 100}],
        "tempo_bpm": 128,
        "max_new_tokens": 64,
        "temperature": 0.8,
        "top_k": 20,
        "prompt_end_beat": 4,
        "pitch_range": [48, 84],
        "version": "v2",
        "repo_id": "example/model",
    }
    assert captured["timeout_seconds"] == 45


def test_mcp_wrapper_reports_generation_timeout(monkeypatch):
    def timed_out(payload, timeout_seconds):
        raise subprocess.TimeoutExpired("midigenai", timeout_seconds)

    monkeypatch.setattr(tool, "_run_bridge_subprocess", timed_out)

    result = tool.generate_midi_continuation(None, notes=[], timeout_seconds=2)

    assert result == "Error generating MIDI continuation: timed out after 2 seconds"


def test_mcp_wrapper_routes_directml_to_isolated_environment(monkeypatch, tmp_path):
    python = tmp_path / ".venv-directml" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(tool, "_DIRECTML_PYTHON", python)
    monkeypatch.delenv("MIDIGENAI_PYTHON", raising=False)
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["payload"] = json.loads(kwargs["input"])
        return subprocess.CompletedProcess(command, 0, '{"notes": []}', "")

    monkeypatch.setattr(tool.subprocess, "run", run)
    result = tool.generate_midi_continuation(None, notes=[], device="directml")

    assert json.loads(result) == {"notes": []}
    assert captured["command"][0] == str(python)
    assert captured["payload"]["device"] == "directml"


def test_generation_python_override_is_validated(monkeypatch, tmp_path):
    missing = tmp_path / "missing.exe"
    monkeypatch.setenv("MIDIGENAI_PYTHON", str(missing))
    with pytest.raises(FileNotFoundError, match="MIDIGENAI_PYTHON"):
        tool._generation_python("directml")


def test_device_environment_routes_gpu_worker(monkeypatch, tmp_path):
    python = tmp_path / "python.exe"
    python.touch()
    monkeypatch.setattr(tool, "_DIRECTML_PYTHON", python)
    monkeypatch.delenv("MIDIGENAI_PYTHON", raising=False)
    monkeypatch.setenv("MIDIGENAI_DEVICE", "directml")
    assert tool._generation_python(None) == str(python)
