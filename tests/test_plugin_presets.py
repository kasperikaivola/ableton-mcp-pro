"""Plugin preset packaging and Live load. No running Live instance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from MCP_Server import serum_preset_codec as codec
from MCP_Server.plugin_presets.registry import register_adapter, unregister_adapter
from MCP_Server.plugin_presets.serum2 import pack_serum_state, unpack_serum_state
from MCP_Server.plugin_presets.vst3 import read_vst3_preset, write_vst3_preset
from MCP_Server.tools import audio_assets
from MCP_Server.tools.plugin_presets import get_user_config, load_plugin_preset
from MCP_Server.userconfig import asset_library_path, load_user_config


ROOT = Path(__file__).resolve().parents[1]
CLASS_ID = b"1234567890ABCDEF1234567890ABCDEF"


def source_preset(path, data, name="Glass Comet", version="2.0.16"):
    document = {
        "metadata": {
            "fileType": "SerumPreset",
            "product": "Serum2",
            "productVersion": version,
            "version": 6,
            "presetName": name,
            "presetAuthor": "MCP",
            "presetDescription": "designed",
            "hash": "opaque",
        },
        "data": data,
    }
    path.write_bytes(codec.encode(document, "preset"))
    return path


def host_template(path, processor, controller, version="2.0.16", info=b"INFO"):
    def chunk(component, data):
        meta = {
            "product": "Serum2",
            "component": component,
            "productVersion": version,
            "version": 6,
        }
        if component == "controller":
            meta.update(presetName="", presetAuthor="", presetDescription="")
        return pack_serum_state(meta, data)

    path.write_bytes(write_vst3_preset(CLASS_ID, {
        b"Comp": chunk("processor", processor),
        b"Cont": chunk("controller", controller),
        b"Info": info,
    }))
    return path


def processor_baseline():
    return {"component": "processor", "Osc": {"level": 1}, "HostOnly": 3}


def controller_baseline():
    return {
        "component": "controller",
        "Osc": {"level": 1},
        "presetName": "",
        "presetAuthor": "",
        "presetDescription": "",
        "presetHasBeenEdited": True,
    }


def write_config(directory, assets, generated, template, host, plugins=None):
    body = {
        "asset_library_path": str(assets),
        "plugins": plugins or {
            "serum2": {
                "device_name": "Serum 2",
                "preset_template": str(template),
                "host_preset_template": str(host),
                "generated_presets_path": str(generated),
                "browser_path": "user_library/MCP Generated/serum2",
            }
        },
    }
    path = directory / "userconfig.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_userconfig_resolves_paths_next_to_the_config_file(tmp_path):
    path = tmp_path / "userconfig.json"
    path.write_text(json.dumps({
        "asset_library_path": "assets",
        "plugins": {
            "serum2": {
                "device_name": "Serum 2",
                "preset_template": "Init.SerumPreset",
                "host_preset_template": "Host.vstpreset",
                "generated_presets_path": "out",
                "browser_path": "user_library/MCP Generated/serum2",
            }
        },
    }), encoding="utf-8")

    config = load_user_config(path)
    serum = config["plugins"]["serum2"]

    assert config["asset_library_path"] == str((tmp_path / "assets").resolve())
    assert serum["generated_presets_path"] == str((tmp_path / "out").resolve())
    assert serum["preset_template"] == str((tmp_path / "Init.SerumPreset").resolve())
    assert serum["browser_path"] == "user_library/MCP Generated/serum2"


def test_userconfig_names_unknown_plugins(tmp_path):
    from MCP_Server.userconfig import require_plugin

    config_path = write_config(
        tmp_path, tmp_path / "assets", tmp_path / "out",
        tmp_path / "Init.SerumPreset", tmp_path / "Host.vstpreset",
    )
    with pytest.raises(ValueError, match="serum2"):
        require_plugin(load_user_config(config_path), "omnisphere")


def test_missing_config_keeps_the_historical_asset_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(tmp_path / "missing.json"))
    assert asset_library_path() == "G:/AudioAssets"


def test_search_uses_configured_asset_library(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "air.wav").write_bytes(b"pcm")
    config_path = write_config(
        tmp_path, assets, tmp_path / "out",
        tmp_path / "Init.SerumPreset", tmp_path / "Host.vstpreset",
    )
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(audio_assets.search_audio_assets(None, "*.wav"))

    assert result["root_path"] == str(assets.resolve())
    assert result["matches"][0]["relative_path"] == "air.wav"


def test_serum_pack_uses_source_state_and_keeps_host_only_fields(tmp_path):
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    before = source.read_bytes(), template.read_bytes()

    from MCP_Server.plugin_presets.registry import pack_plugin_preset
    packed, report = pack_plugin_preset("serum2", source, template)
    class_id, chunks = read_vst3_preset(packed)
    processor = unpack_serum_state(chunks[b"Comp"])[1]
    controller = unpack_serum_state(chunks[b"Cont"])[1]

    assert class_id == CLASS_ID
    assert processor["Osc"] == {"level": 0.25}
    assert processor["HostOnly"] == 3
    assert processor["component"] == "processor"
    assert controller["presetName"] == "Glass Comet"
    assert controller["presetHasBeenEdited"] is False
    assert chunks[b"Info"] == b"INFO"
    assert report["version"] == "2.0.16"
    assert source.read_bytes() == before[0]
    assert template.read_bytes() == before[1]


def test_serum_pack_rejects_cross_version_and_unmapped_fields(tmp_path):
    from MCP_Server.plugin_presets.registry import pack_plugin_preset

    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    newer = source_preset(
        tmp_path / "Newer.SerumPreset", {"Osc": {"level": 0.2}}, version="2.0.17",
    )
    with pytest.raises(ValueError, match="productVersion"):
        pack_plugin_preset("serum2", newer, template)

    extra = source_preset(tmp_path / "Extra.SerumPreset", {"Osc": {"level": 0.2}, "Filter": 1})
    with pytest.raises(ValueError, match="Filter"):
        pack_plugin_preset("serum2", extra, template)


def test_registry_rejects_a_plugin_without_an_adapter():
    from MCP_Server.plugin_presets.registry import pack_plugin_preset

    with pytest.raises(ValueError, match="other-synth"):
        pack_plugin_preset("other-synth", Path("missing"), Path("missing"))


class Live:
    def __init__(self, before, after, items_for):
        self.before = before
        self.after = after
        self.items_for = items_for
        self.calls = []
        self.loaded = False
        self.fail_on = None

    def send_command(self, command, params):
        self.calls.append((command, dict(params)))
        if command == self.fail_on:
            raise RuntimeError("Live unavailable")
        if command == "create_midi_track":
            return {"index": 7, "name": "7-MIDI"}
        if command == "set_track_name":
            return {"name": params["name"]}
        if command == "get_track_info":
            return self.after if self.loaded else self.before
        if command == "get_arrangement_clips":
            state = self.after if self.loaded else self.before
            return {"arrangement_clip_count": state["arrangement_clip_count"], "clips": []}
        if command == "get_browser_items_at_path":
            return {"path": params["path"], "items": self.items_for(params["path"])}
        if command == "load_browser_item":
            self.loaded = True
            return {"loaded": True, "uri": params["item_uri"]}
        if command == "get_device_parameters":
            return {"parameters": [{"name": "A Level", "value": 0.25}]}
        raise AssertionError(command)


def midi_track(devices, clips=None, arrangement=0, kind="regular", audio=False, midi=True):
    return {
        "index": 4,
        "name": "Bass",
        "kind": kind,
        "is_audio_track": audio,
        "is_midi_track": midi,
        "clip_slots": clips if clips is not None else [{"index": 0, "has_clip": True}],
        "devices": devices,
        "arrangement_clip_count": arrangement,
    }


def serum_device(index):
    return {"index": index, "name": "Serum 2", "class_name": "PluginDevice", "type": "instrument"}


def publish_items(directory):
    def items(_path):
        return [
            {"name": path.name, "uri": f"query:UserLibrary#{path.name}", "is_loadable": True}
            for path in directory.glob("*.vstpreset")
        ]
    return items


def test_new_track_load_publishes_a_new_file_and_verifies_serum(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    before = midi_track([], clips=[], arrangement=0)
    before["index"] = 7
    before["name"] = "Glass Comet"
    after = midi_track([serum_device(0)], clips=[], arrangement=0)
    after["index"] = 7
    after["name"] = "Glass Comet"
    live = Live(before, after, publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source)))

    assert result["loaded"] is True
    assert result["track_index"] == 7
    assert result["track_name"] == "Glass Comet"
    assert result["device_index"] == 0
    assert result["browser_uri"].startswith("query:UserLibrary#")
    assert Path(result["output_path"]).parent == generated.resolve()
    assert Path(result["output_path"]).resolve() not in {source.resolve(), template.resolve()}
    assert source.read_bytes()
    assert template.read_bytes()
    assert [call[0] for call in live.calls].count("create_midi_track") == 1
    assert live.calls[1] == ("set_track_name", {"track_index": 7, "name": "Glass Comet"})
    assert "delete_device" not in [call[0] for call in live.calls]
    assert result["configure_parameter_count"] == 1
    assert result["state_verified"] == []


def test_replace_keeps_clips_and_effects(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Existing Bass.SerumPreset", {"Osc": {"level": 0.5}}, name="Existing Bass")
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    fx = [
        {"index": 0, "name": "Arpeggiator", "class_name": "Arpeggiator", "type": "midi_effect"},
        {"index": 1, "name": "Operator", "class_name": "Operator", "type": "instrument"},
        {"index": 2, "name": "Reverb", "class_name": "Reverb", "type": "audio_effect"},
    ]
    before = midi_track(fx, arrangement=2)
    after_devices = [
        {"index": 0, "name": "Arpeggiator", "class_name": "Arpeggiator", "type": "midi_effect"},
        serum_device(1),
        {"index": 2, "name": "Reverb", "class_name": "Reverb", "type": "audio_effect"},
    ]
    after = midi_track(after_devices, arrangement=2)
    live = Live(before, after, publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source), track_index=4))

    assert result["loaded"] is True
    assert result["replaced_instrument"] == "Operator"
    assert result["clips_unchanged"] is True
    assert result["effects_unchanged"] is True
    assert "create_midi_track" not in [call[0] for call in live.calls]
    assert "set_track_name" not in [call[0] for call in live.calls]
    load_calls = [call for call in live.calls if call[0] == "load_browser_item"]
    assert len(load_calls) == 1
    assert load_calls[0][1]["track_index"] == 4


def test_second_instrument_is_reported_without_deletion(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Stack.SerumPreset", {"Osc": {"level": 0.5}}, name="Stack")
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    before = midi_track([
        {"index": 0, "name": "Operator", "class_name": "Operator", "type": "instrument"},
        {"index": 1, "name": "Reverb", "class_name": "Reverb", "type": "audio_effect"},
    ])
    after = midi_track([
        {"index": 0, "name": "Operator", "class_name": "Operator", "type": "instrument"},
        serum_device(1),
        {"index": 2, "name": "Reverb", "class_name": "Reverb", "type": "audio_effect"},
    ])
    live = Live(before, after, publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source), track_index=4))

    assert result["loaded"] is False
    assert "instrument" in result["error"].lower()
    assert Path(result["output_path"]).is_file()
    assert "delete_device" not in [call[0] for call in live.calls]


def test_unavailable_live_writes_nothing(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    live = Live(midi_track([]), midi_track([]), publish_items(generated))
    live.fail_on = "create_midi_track"
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source)))

    assert result["loaded"] is False
    assert "Live unavailable" in result["error"]
    assert list(generated.glob("*.vstpreset")) == []


def test_audio_track_is_rejected_before_publish(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    live = Live(midi_track([], audio=True, midi=False), midi_track([]), publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source), track_index=4))

    assert result["loaded"] is False
    assert list(generated.glob("*.vstpreset")) == []
    assert "load_browser_item" not in [call[0] for call in live.calls]


def test_browser_miss_keeps_the_new_file(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    live = Live(midi_track([], clips=[], arrangement=0), midi_track([]), lambda _path: [])
    live.before["index"] = 7
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.ATTEMPTS", 2)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source)))

    assert result["loaded"] is False
    assert "indexed" in result["error"].lower()
    assert Path(result["output_path"]).is_file()
    assert "load_browser_item" not in [call[0] for call in live.calls]


def test_existing_publish_name_gets_a_second_file(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "Glass Comet.vstpreset").write_bytes(b"already")
    source = source_preset(tmp_path / "Glass Comet.SerumPreset", {"Osc": {"level": 0.25}})
    template = host_template(tmp_path / "Host.vstpreset", processor_baseline(), controller_baseline())
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template)
    before = midi_track([], clips=[], arrangement=0)
    before["index"] = 7
    after = midi_track([serum_device(0)], clips=[], arrangement=0)
    after["index"] = 7
    live = Live(before, after, publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(load_plugin_preset(None, "serum2", str(source)))

    assert result["loaded"] is True
    assert Path(result["output_path"]).name != "Glass Comet.vstpreset"
    assert (generated / "Glass Comet.vstpreset").read_bytes() == b"already"


def test_custom_adapter_uses_the_same_loader(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    source = tmp_path / "patch.other"
    source.write_bytes(b"source-preset")
    template = tmp_path / "host.vstpreset"
    template.write_bytes(b"host-template")
    plugins = {
        "other-synth": {
            "device_name": "Other Synth",
            "preset_template": str(source),
            "host_preset_template": str(template),
            "generated_presets_path": str(generated),
            "browser_path": "user_library/MCP Generated/other-synth",
        }
    }
    config_path = write_config(tmp_path, tmp_path / "assets", generated, source, template, plugins)

    def pack(source_path, template_path):
        assert Path(source_path).read_bytes() == b"source-preset"
        assert Path(template_path).read_bytes() == b"host-template"
        return b"VST3-OTHER", {"version": "1", "preset_name": "Other Patch"}

    register_adapter("other-synth", pack)
    before = midi_track([], clips=[], arrangement=0)
    before["index"] = 7
    after = midi_track(
        [{"index": 0, "name": "Other Synth", "class_name": "PluginDevice", "type": "instrument"}],
        clips=[], arrangement=0,
    )
    after["index"] = 7
    live = Live(before, after, publish_items(generated))
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.get_ableton_connection", lambda: live)
    monkeypatch.setattr("MCP_Server.tools.plugin_presets.PAUSE_SECONDS", 0)
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))
    try:
        result = json.loads(load_plugin_preset(None, "other-synth", str(source), track_name="Other Patch"))
    finally:
        unregister_adapter("other-synth")

    assert result["loaded"] is True
    assert result["device_name"] == "Other Synth"
    assert Path(result["output_path"]).read_bytes() == b"VST3-OTHER"
    assert source.read_bytes() == b"source-preset"
    assert template.read_bytes() == b"host-template"


def test_get_user_config_returns_the_serum_template(tmp_path, monkeypatch):
    config_path = write_config(
        tmp_path, tmp_path / "assets", tmp_path / "out",
        tmp_path / "Init.SerumPreset", tmp_path / "Host.vstpreset",
    )
    monkeypatch.setenv("ABLETON_MCP_USERCONFIG", str(config_path))

    result = json.loads(get_user_config(None))

    assert result["plugins"]["serum2"]["preset_template"].endswith("Init.SerumPreset")
    assert result["asset_library_path"] == str((tmp_path / "assets").resolve())


def test_new_preset_instructions_require_a_new_design():
    for relative in (
        ".agents/skills/synth-sound-design/SKILL.md",
        ".claude/skills/synth-sound-design/SKILL.md",
        "MCP_Server/synth_guides/serum-presets.md",
        "AGENTS.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "one or two parameters" in text
        assert "load_plugin_preset" in text


