from pathlib import Path
import sys
import types

import pytest

from tools import midigenai_bridge as bridge


def test_generator_cache_reuses_loaded_model(monkeypatch):
    calls = []
    midigenai = types.ModuleType("midigenai")

    def load_from_hub(*, version, repo_id):
        calls.append((version, repo_id))
        return object()

    midigenai.load_from_hub = load_from_hub
    monkeypatch.setitem(sys.modules, "midigenai", midigenai)
    monkeypatch.setattr(bridge, "_GENERATOR", None)

    first = bridge._get_generator("repo", "version")
    second = bridge._get_generator("repo", "version")

    assert first is second
    assert calls == [("version", "repo")]


def test_directml_device_is_forwarded_and_cached_separately(monkeypatch):
    calls = []
    midigenai = types.ModuleType("midigenai")
    directml = types.ModuleType("torch_directml")
    gpu = object()
    directml.device = lambda: gpu

    def load_from_hub(**kwargs):
        calls.append(kwargs)
        return object()

    midigenai.load_from_hub = load_from_hub
    monkeypatch.setitem(sys.modules, "midigenai", midigenai)
    monkeypatch.setitem(sys.modules, "torch_directml", directml)
    monkeypatch.setattr(bridge, "_GENERATOR", None)

    default = bridge._get_generator("repo", "version")
    first = bridge._get_generator("repo", "version", "directml")
    second = bridge._get_generator("repo", "version", "directml")

    assert first is second
    assert first is not default
    assert calls[-1] == {
        "version": "version", "repo_id": "repo", "device": gpu, "backend": "torch"
    }


def test_invalid_device_is_rejected_before_loading(monkeypatch):
    with pytest.raises(ValueError, match="device must be"):
        bridge._get_generator("repo", "version", "invalid")


def test_explicit_cpu_device_is_forwarded(monkeypatch):
    calls = []
    midigenai = types.ModuleType("midigenai")
    torch = types.ModuleType("torch")
    torch.device = lambda name: name
    midigenai.load_from_hub = lambda **kwargs: calls.append(kwargs) or object()
    monkeypatch.setitem(sys.modules, "midigenai", midigenai)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(bridge, "_GENERATOR", None)
    bridge._get_generator("repo", "version", "cpu")
    assert calls == [{
        "version": "version", "repo_id": "repo", "device": "cpu", "backend": "torch"
    }]


def test_missing_directml_has_specific_install_hint(monkeypatch):
    monkeypatch.setattr(bridge, "_GENERATOR", None)
    monkeypatch.setitem(sys.modules, "torch_directml", None)
    monkeypatch.setitem(sys.modules, "midigenai", types.ModuleType("midigenai"))
    with pytest.raises(bridge.MidigenAIDependencyError, match="torch-directml"):
        bridge._get_generator("repo", "version", "directml")


def test_generation_cleans_temporary_midis_when_generation_fails(monkeypatch):
    created = []

    class FakeScore:
        def dump_midi(self, path):
            path = Path(path)
            path.write_bytes(b"input")
            created.append(path)

    class FailingGenerator:
        def encode_midi_file(self, path):
            return [1, 2]

        def generate_to_midi(self, prompt_ids, path, **kwargs):
            path = Path(path)
            path.write_bytes(b"output")
            created.append(path)
            raise RuntimeError("generation failed")

    monkeypatch.setattr(bridge, "notes_to_score", lambda notes, tempo: FakeScore())
    monkeypatch.setattr(bridge, "_get_generator", lambda repo_id, version: FailingGenerator())

    with pytest.raises(RuntimeError, match="generation failed"):
        bridge.generate_midi_continuation([{"pitch": 60, "start_time": 0, "duration": 1, "velocity": 100}])

    assert created
    assert all(not path.exists() for path in created)
