"""Small local library checks; no Live or external asset dependency."""

import json

import pytest

from MCP_Server.tools.audio_assets import _matcher, _search, search_audio_assets


@pytest.fixture
def library(tmp_path):
    for name in ["Init.SerumPreset", "packs/Serum Pads/Deep/Mystic PAD.serumpreset",
                 "packs/Serum Pads/Soft Pad.SerumPreset", "old/Pad.fxp", "samples/air.wav"]:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"candidate only")
    return tmp_path


def test_recursive_case_and_path_globs(library):
    result = _search("*pad*.SerumPreset", str(library), 0, 30, 1000)
    assert len(result["matches"]) == 2 and result["scan_complete"]
    assert all(x["serum_preset_candidate"] for x in result["matches"])
    result = _search("**/Serum*/**/*.SerumPreset", str(library), 0, 30, 1000)
    assert len(result["matches"]) == 2
    assert _matcher("**/*.SerumPreset")("Init.SerumPreset")
    assert not _matcher("packs/*.SerumPreset")("packs/deep/pad.SerumPreset")
    assert _matcher("*p[ae]d?.wav")("nested/pad1.wav")


def test_pagination_and_legacy_flag(library):
    first = _search("*.SerumPreset", str(library), 0, 1, 1000)
    assert first["next_offset"] == 1 and not first["scan_complete"]
    second = _search("*.SerumPreset", str(library), 1, 10, 1000)
    assert len(second["matches"]) == 2
    assert first["matches"][0] not in second["matches"]
    legacy = _search("*.fxp", str(library), 0, 30, 1000)["matches"][0]
    assert legacy["legacy_serum_fxp"] and not legacy["serum_preset_candidate"]


def test_scan_limit_and_invalid_patterns(library):
    result = _search("missing*", str(library), 0, 30, 1)
    assert not result["scan_complete"] and result["stop_reason"] == "entry_limit"
    for pattern in ["../*.wav", "G:/AudioAssets/*.wav", "/absolute", ""]:
        with pytest.raises(ValueError):
            _matcher(pattern)
    assert "error" in json.loads(search_audio_assets(None, root_path=str(library), limit=101))


def test_directory_link_is_not_traversed(library, tmp_path):
    link = library / "loop"
    try:
        link.symlink_to(library, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not permit symlink creation for this test process")
    result = _search("*.SerumPreset", str(library), 0, 30, 1000)
    assert result["skipped_links"] == 1 and len(result["matches"]) == 3
    assert not result["scan_complete"]
