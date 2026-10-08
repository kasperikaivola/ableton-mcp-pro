"""Focused offline safety/fidelity checks; no copyrighted preset fixtures."""

import copy
import json
import struct

import pytest

from MCP_Server import serum_preset_codec as codec
from MCP_Server import serum_preset_tree as tree
from MCP_Server.tools import serum_presets as tools


@pytest.fixture
def document():
    return {
        "metadata": {"fileType": "SerumPreset", "product": "Serum2", "productVersion": "2.0.14",
                     "presetName": "Synthetic", "hash": "opaque-preserved"},
        "data": {"Env0": {"plainParams": {"kParamDecay": 0.5}},
                 "Oscillator0": {"SampleOsc0": {"embedded_audio": {"data": [[0.1] * 1000, [0.2] * 1000]},
                                                "sampleRate": 48000}},
                 "LFO0": {"plainParams": "default"},
                 "unknown/module~": {"future": [1, 2, 3]}},
    }


@pytest.fixture
def source(tmp_path, document):
    path = tmp_path / "source.SerumPreset"
    path.write_bytes(codec.encode(document, "preset"))
    return path


def response(func, **kwargs):
    return json.loads(func(None, **kwargs))


def test_binary_json_roundtrip_and_opaque_types(document):
    raw = codec.encode(document, "preset")
    decoded, kind = codec.decode(raw)
    assert decoded == document and kind == "preset"
    assert codec.decode(codec.encode(decoded, "json"))[0] == document
    decoded["data"]["futureBytes"] = b"\x00\xff"
    assert codec.decode(codec.encode(decoded, "preset"))[0] == decoded
    with pytest.raises(ValueError, match="Non-JSON"):
        codec.encode(decoded, "json")


def test_malformed_headers_and_json(document):
    raw = codec.encode(document, "preset")
    length = struct.unpack_from("<Q", raw, 9)[0]
    off = 17 + length
    for broken in [raw[:15], raw[:18], raw[:off] + struct.pack("<II", 1, 99) + raw[off+8:],
                   raw[:off] + struct.pack("<II", 1, 2) + raw[off+8:], raw + b"trailing"]:
        with pytest.raises(Exception):
            codec.decode(broken)
    with pytest.raises(ValueError, match="Duplicate"):
        codec.strict_json('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="Non-finite"):
        codec.strict_json('{"a":NaN}')
    with pytest.raises(ValueError, match="Only Serum2"):
        codec.decode(b'{"metadata":{},"data":{}}')


def test_size_limits(monkeypatch, document):
    raw = codec.encode(document, "preset")
    monkeypatch.setattr(codec, "MAX_BYTES", 100)
    with pytest.raises(ValueError, match="limit"):
        codec.decode(raw)
    with pytest.raises(ValueError, match="limit"):
        codec.encode(document, "preset")


def test_bounded_reads_arrays_and_escaped_paths(document):
    assert tree.get(document, "/data/unknown~1module~0/future/1") == 2
    result = tree.read(document, "/data/Oscillator0", depth=5)
    assert len(json.dumps(result)) < 3000
    channel = "/data/Oscillator0/SampleOsc0/embedded_audio/data/0"
    result = tree.read(document, channel, offset=5, limit=2)
    assert result["total"] == 1000 and result["next_offset"] == 7
    assert [x["value"] for x in result["entries"]] == [0.1, 0.1]
    with pytest.raises(ValueError):
        tree.get(document, channel + "/01")
    with pytest.raises(ValueError):
        tree.get(document, "/data/unknown~2module")
    with pytest.raises(ValueError):
        tree.read(document, "", limit=101)


def test_search_skips_audio_and_paginates(document):
    result = tree.search(document, "0.1", pointer="/data")
    assert not result["matches"] and len(result["skipped_large_arrays"]) == 2
    result = tree.search(document, "0.1", pointer="/data", include_array_values=True, limit=2)
    assert len(result["matches"]) == 2 and result["next_offset"] == 2
    next_page = tree.search(document, "0.1", pointer="/data", include_array_values=True, limit=2, offset=2)
    assert next_page["matches"][0]["path"].endswith("/2")
    result = tree.search(document, "kparamdecay")
    assert result["matches"] == [{"path": "/data/Env0/plainParams/kParamDecay", "value": 0.5}]


def test_patch_batch_preserves_assets_and_unknowns(document):
    original = copy.deepcopy(document)
    operations = [
        {"op": "test", "path": "/data/Env0/plainParams/kParamDecay", "value": 0.5},
        {"op": "replace", "path": "/data/Env0/plainParams/kParamDecay", "value": 0.6},
        {"op": "replace", "path": "/data/LFO0/plainParams", "value": {}},
        {"op": "add", "path": "/data/LFO0/plainParams/kParamRate", "value": 1},
        {"op": "add", "path": "/data/unknown~1module~0/future/-", "value": 4},
        {"op": "remove", "path": "/data/unknown~1module~0/future/0"},
    ]
    edited, _ = tree.patch(document, operations)
    assert document == original
    assert edited["data"]["Oscillator0"] == original["data"]["Oscillator0"]
    assert edited["metadata"] == original["metadata"]
    assert tree.get(edited, "/data/unknown~1module~0/future") == [2, 3, 4]
    changed = tree.compare(original, edited)
    assert len(changed["changes"]) == 5


def test_edit_dryrun_stale_batch_and_output_safety(source, tmp_path, document):
    target = tmp_path / "edited.SerumPreset"
    raw = source.read_bytes()
    args = dict(file_path=str(source), expected_sha256=codec.digest(raw),
                operations=[{"op": "replace", "path": "/data/Env0/plainParams/kParamDecay", "value": 0.6}],
                output_path=str(target))
    assert response(tools.edit_serum_preset, **args)["dry_run"] is True
    assert not target.exists()
    stale = {**args, "expected_sha256": "wrong", "dry_run": False}
    assert "error" in response(tools.edit_serum_preset, **stale) and not target.exists()
    invalid = {**args, "operations": args["operations"] + [{"op": "remove", "path": "/data/missing"}], "dry_run": False}
    assert "error" in response(tools.edit_serum_preset, **invalid) and not target.exists()
    result = response(tools.edit_serum_preset, **args, dry_run=False)
    assert result["live_applied"] is False and "error" not in result
    assert source.read_bytes() == raw
    edited = codec.load(str(target))[1]
    expected = copy.deepcopy(document)
    expected["data"]["Env0"]["plainParams"]["kParamDecay"] = 0.6
    assert edited == expected
    assert "error" in response(tools.edit_serum_preset, **args, dry_run=False)
    assert "error" in response(tools.edit_serum_preset, **{**args, "output_path": str(source)}, dry_run=False, overwrite=True)
    alias = tmp_path / "alias.SerumPreset"
    import os
    os.link(source, alias)
    assert "error" in response(tools.edit_serum_preset, **{**args, "output_path": str(alias)}, dry_run=False, overwrite=True)
    assert source.read_bytes() == raw


def test_offline_conversion_and_compare_tools(source, tmp_path):
    info = response(tools.get_serum_preset_info, file_path=str(source))
    exported = tmp_path / "exported.json"
    result = response(tools.convert_serum_preset, file_path=str(source),
                      output_path=str(exported), output_format="json",
                      expected_sha256=info["source_sha256"])
    assert exported.exists() and "error" not in result
    assert response(tools.compare_serum_presets, left_path=str(source), right_path=str(exported))["equal"]
    assert response(tools.read_serum_preset, file_path=str(source), path="/data/Env0/plainParams")["entries"][0]["value"] == 0.5
    assert response(tools.search_serum_preset, file_path=str(source), query="kParamDecay")["matches"]


def test_compare_pagination_and_failed_test(document):
    changed = copy.deepcopy(document)
    changed["metadata"]["presetName"] = "New"
    changed["data"]["Env0"]["plainParams"]["kParamDecay"] = 0.7
    page = tree.compare(document, changed, limit=1)
    assert not page["equal"] and page["next_offset"] == 1
    assert tree.compare(document, changed, offset=1, limit=1)["changes"][0]["path"].endswith("kParamDecay")
    with pytest.raises(ValueError, match="Test failed"):
        tree.patch(document, [{"op": "test", "path": "/metadata/presetName", "value": "wrong"}])


def test_mapping_views_do_not_materialize_all_items():
    class LimitedItems(dict):
        def items(self):
            for i in range(100000):
                if i >= 20:
                    raise AssertionError("Bounded view consumed the entire mapping")
                yield str(i), i

    values = LimitedItems({str(i): i for i in range(30)})
    assert len(tree.summary(values, depth=1)["entries"]) == 20
    assert len(tree.read(values, "", limit=2)["entries"]) == 2


def test_response_cap_and_pointer_limit():
    reply = tools._reply(lambda: {"skipped_large_arrays": [{"path": "x" * 100000}],
                                  "live_applied": False})
    assert len(reply) <= 32000 and json.loads(reply)["details_omitted"]
    with pytest.raises(ValueError, match="4096"):
        tree.tokens("/" + "x" * 5000)


def test_boolean_numeric_changes_are_not_hidden(document):
    left = copy.deepcopy(document)
    left["data"]["enabled"] = True
    right = copy.deepcopy(left)
    right["data"]["enabled"] = 1
    assert tree.compare(left, right)["changes"][0]["path"] == "/data/enabled"
    with pytest.raises(ValueError, match="Test failed"):
        tree.patch(left, [{"op": "test", "path": "/data/enabled", "value": 1}])


def test_copy_keeps_complete_opaque_state_and_array_semantics(document):
    document["data"]["asset"] = {"blob": b"\x00\xff", "samples": [0.25] * 10000}
    edited, _ = tree.patch(document, [
        {"op": "copy", "from": "/data/asset", "path": "/data/assetCopy"},
        {"op": "copy", "from": "/data/unknown~1module~0/future/0",
         "path": "/data/unknown~1module~0/future/1"},
    ])
    assert edited["data"]["assetCopy"] == document["data"]["asset"]
    assert edited["data"]["assetCopy"] is not edited["data"]["asset"]
    assert tree.get(edited, "/data/unknown~1module~0/future") == [1, 1, 2, 3]
    assert "assetCopy" not in document["data"]


def test_reference_copy_json_edit_repack_full_modules(tmp_path, document):
    donor = copy.deepcopy(document)
    donor["data"].update({
        "WT": {"relativePathToWT": "Synthetic.wav", "numFrames": 10000,
               "embeddedWTData": [0.25] * 10000, "plainParams": {"kParamTablePos": 1.0}},
        "FXRack0": {"FX": [{"type": 0, "FXDistortion": {"plainParams": {"kParamWet": 25.0}},
                            "future": {"retain": [1, 2]}}]},
        "ModSlot0": {"source": [3, 0], "destModuleTypeString": "VoiceFilter",
                     "destModuleID": 0, "destModuleParamID": 3,
                     "destModuleParamName": "kParamFreq", "plainParams": {"kParamAmount": 10.0}},
    })
    original = tmp_path / "original.SerumPreset"
    donor_file = tmp_path / "donor.SerumPreset"
    original.write_bytes(codec.encode(document, "preset"))
    donor_file.write_bytes(codec.encode(donor, "preset"))
    original_raw, donor_raw = original.read_bytes(), donor_file.read_bytes()
    unpacked, edited_json, packed = (tmp_path / name for name in ("unpacked.json", "edited.json", "edited.SerumPreset"))
    assert "error" not in response(tools.convert_serum_preset, file_path=str(original),
        output_path=str(unpacked), output_format="json", expected_sha256=codec.digest(original_raw))
    ops = [{"op": "copy", "from": "/data/" + module, "path": "/data/" + module,
            "source_file_path": str(donor_file), "source_sha256": codec.digest(donor_raw)}
           for module in ("WT", "FXRack0", "ModSlot0")]
    ops += [{"op": "replace", "path": "/data/Env0/plainParams/kParamDecay", "value": 0.2},
            {"op": "replace", "path": "/data/FXRack0/FX/0/FXDistortion/plainParams/kParamWet", "value": 40.0}]
    result = response(tools.edit_serum_preset, file_path=str(unpacked),
        expected_sha256=codec.digest(unpacked.read_bytes()), operations=ops,
        output_path=str(edited_json), output_format="json", dry_run=False)
    assert "error" not in result
    assert "error" not in response(tools.convert_serum_preset, file_path=str(edited_json),
        expected_sha256=result["output_sha256"], output_path=str(packed), output_format="preset")
    expected = copy.deepcopy(document)
    for module in ("WT", "FXRack0", "ModSlot0"):
        expected["data"][module] = copy.deepcopy(donor["data"][module])
    expected["data"]["Env0"]["plainParams"]["kParamDecay"] = 0.2
    expected["data"]["FXRack0"]["FX"][0]["FXDistortion"]["plainParams"]["kParamWet"] = 40.0
    assert codec.load(str(packed))[1] == expected
    assert response(tools.compare_serum_presets, left_path=str(edited_json), right_path=str(packed))["equal"]
    assert original.read_bytes() == original_raw and donor_file.read_bytes() == donor_raw


def test_external_copy_guards_and_opaque_binary(source, tmp_path, document, monkeypatch):
    donor = tmp_path / "donor.SerumPreset"
    document["data"]["opaque"] = {"raw": b"\xff", "samples": [0.5] * 10000}
    donor.write_bytes(codec.encode(document, "preset"))
    output = tmp_path / "out.SerumPreset"
    op = {"op": "copy", "from": "/data/opaque", "path": "/data/new",
          "source_file_path": str(donor), "source_sha256": codec.digest(donor.read_bytes())}
    args = dict(file_path=str(source), expected_sha256=codec.digest(source.read_bytes()),
                operations=[op], output_path=str(output), dry_run=False)
    for broken in ({**op, "source_sha256": "stale"},
                   {k: v for k, v in op.items() if k != "source_sha256"},
                   {**op, "from": "/data/missing"}):
        assert "error" in response(tools.edit_serum_preset, **{**args, "operations": [broken]})
        assert not output.exists()
    assert "error" not in response(tools.edit_serum_preset, **args)
    assert codec.load(str(output))[1]["data"]["new"] == document["data"]["opaque"]
    assert "error" in response(tools.edit_serum_preset, **{**args,
        "output_path": str(tmp_path / "opaque.json"), "output_format": "json"})
    real_encode = codec.encode

    def changed_donor(*args):
        raw = real_encode(*args)
        donor.write_bytes(donor.read_bytes() + b"changed")
        return raw

    monkeypatch.setattr(codec, "encode", changed_donor)
    raced = tmp_path / "raced.SerumPreset"
    result = response(tools.edit_serum_preset, **{**args, "output_path": str(raced)})
    assert "Copy source changed" in result["error"] and not raced.exists()
