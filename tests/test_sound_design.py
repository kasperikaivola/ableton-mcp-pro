"""Offline guide contract; no Live or plug-in state is mutated."""

import asyncio
import json

import pytest

from MCP_Server import runtime
from MCP_Server.tools import devices_browser, sound_design


def read(synth="overview", section="index"):
    return json.loads(sound_design.get_synth_sound_design_guide(None, synth, section))


@pytest.mark.parametrize("synth", ["overview", "serum2", "omnisphere", "serum-presets"])
def test_all_indexed_sections_are_available_offline(monkeypatch, synth):
    def no_live():
        raise AssertionError("Reference retrieval must not connect to Live")

    monkeypatch.setattr(runtime, "get_ableton_connection", no_live)
    index = read(synth)
    assert "error" not in index
    assert {"sources"} <= index["sections"].keys()
    whole = read(synth, "all")["content"]
    for section, title in index["sections"].items():
        result = read(synth, section)
        assert result["section"] == section
        assert result["content"].startswith(f"## {title}\n")
        assert result["content"] in whole
    assert "not applied — set manually" in index["instructions"]
    assert "suggestions alone" in index["instructions"]


@pytest.mark.parametrize("alias, expected", [
    (" Serum 2 ", "serum2"), ("serum", "serum2"), ("serum-2", "serum2"),
    ("Omnisphere 2", "omnisphere"), ("omnisphere3", "omnisphere"),
])
def test_friendly_synth_aliases(alias, expected):
    assert read(alias)["synth"] == expected


@pytest.mark.parametrize("synth, section", [
    ("../../AGENTS", "all"), ("unknown", "index"),
    ("serum2", "../../AGENTS.md"), ("omnisphere", "missing"),
])
def test_invalid_input_returns_actionable_choices(synth, section):
    result = read(synth, section)
    assert "error" in result
    assert result["available_synths"] == ["overview", "serum2", "omnisphere", "serum-presets"]
    assert "content" not in result
    if synth in result["available_synths"]:
        assert "identity" in result["sections"]


def test_missing_packaged_reference_returns_error(monkeypatch):
    def missing(_):
        raise ModuleNotFoundError("No bundled reference package")

    monkeypatch.setattr(sound_design, "files", missing)
    assert "Bundled guide unavailable" in read("serum2")["error"]


def test_guide_is_registered_with_mcp():
    registered = asyncio.run(runtime.mcp.list_tools())
    tool = next(tool for tool in registered if tool.name == "get_synth_sound_design_guide")
    assert "Serum 2" in tool.description and "Omnisphere" in tool.description
    assert tool.inputSchema["properties"]["synth"]["default"] == "overview"


@pytest.mark.parametrize("name", ["Omnisphere", "Renamed instrument"])
def test_plugin_inventory_routes_to_guide_without_changing_snapshot(monkeypatch, name):
    snapshot = {"device_name": name, "class_name": "PluginDevice", "parameters": []}

    class Connection:
        def send_command(self, command, params):
            assert command == "get_device_parameters"
            assert "query" not in params
            return snapshot

    monkeypatch.setattr(devices_browser, "get_ableton_connection", lambda: Connection())
    result = json.loads(devices_browser.get_device_parameters(None, 0, 0))
    assert "get_synth_sound_design_guide" in result["manual_settings_handoff"]
    assert "Omnisphere — manual settings" in result["manual_settings_handoff"]
    assert result["parameters"] == []
    assert "manual_settings_handoff" not in snapshot
