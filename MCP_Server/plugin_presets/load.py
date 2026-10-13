"""Publish a new host preset and load it through Live's browser."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import time

from .. import serum_preset_codec as codec
from ..userconfig import load_user_config, require_plugin
from .registry import pack_plugin_preset


LIMITS = (
    "Same-build host preset. Configure readback is not a full preset comparison. "
    "No audio audition."
)


def _stem(name: str) -> str:
    cleaned = []
    for char in name:
        if char in '<>:"/\\|?*' or ord(char) < 32:
            cleaned.append(" ")
        else:
            cleaned.append(char)
    text = " ".join("".join(cleaned).split()).strip().rstrip(".")
    return (text or "Preset")[:80]


def _conflicts(path: Path, forbidden: set[Path]) -> bool:
    resolved = path.resolve()
    if resolved in forbidden:
        return True
    for other in forbidden:
        try:
            if path.exists() and other.exists() and os.path.samefile(path, other):
                return True
        except OSError:
            continue
    return False


def publish_new_bytes(directory: Path, stem: str, payload: bytes, forbidden: set[Path]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stem = _stem(stem)
    digest = hashlib.sha256(payload).hexdigest()[:8]
    candidates = [
        directory / f"{stem}.vstpreset",
        directory / f"{stem}-{digest}.vstpreset",
    ]
    for path in candidates:
        if _conflicts(path, forbidden) or path.exists():
            continue
        try:
            with path.open("xb") as stream:
                stream.write(payload)
        except FileExistsError:
            continue
        return path
    raise ValueError("Could not publish a new preset file without overwriting an existing file.")


def _snapshot(connection, track_index: int) -> dict:
    info = dict(connection.send_command("get_track_info", {"track_index": track_index}))
    arrangement = connection.send_command(
        "get_arrangement_clips", {"track_index": track_index}
    )
    info["arrangement_clip_count"] = arrangement.get("arrangement_clip_count", 0)
    return info


def _prepare_track(connection, track_index, track_name, preset_name):
    if track_index is None:
        created = connection.send_command("create_midi_track", {"index": -1})
        index = created["index"]
        name = track_name or preset_name or "Preset"
        connection.send_command("set_track_name", {"track_index": index, "name": name})
        info = _snapshot(connection, index)
        info["name"] = name
        return info
    if type(track_index) is not int or isinstance(track_index, bool) or track_index < 0:
        raise ValueError("track_index must be a regular MIDI track.")
    info = _snapshot(connection, track_index)
    kind = info.get("kind")
    if kind != "regular" or not info.get("is_midi_track") or info.get("is_audio_track"):
        raise ValueError(
            "Choose a regular MIDI track. Audio, group, return, and master tracks are not loaded."
        )
    return info


def _find_uri(connection, browser_path: str, output: Path, attempts: int, pause_seconds: float):
    wanted = {output.name.casefold(), output.stem.casefold()}
    for attempt in range(attempts):
        result = connection.send_command(
            "get_browser_items_at_path", {"path": browser_path}
        )
        for item in result.get("items") or []:
            name = str(item.get("name") or "").casefold()
            if name in wanted and item.get("uri"):
                return item["uri"]
        if attempt + 1 < attempts and pause_seconds:
            time.sleep(pause_seconds)
    return None


def _verify(before: dict, after: dict, device_name: str) -> dict:
    def split(devices):
        instruments = [device for device in devices if device.get("type") == "instrument"]
        others = [device for device in devices if device.get("type") != "instrument"]
        return instruments, others

    before_instruments, before_effects = split(before.get("devices") or [])
    after_instruments, after_effects = split(after.get("devices") or [])
    clips_unchanged = (
        [slot.get("has_clip") for slot in before.get("clip_slots") or []]
        == [slot.get("has_clip") for slot in after.get("clip_slots") or []]
        and before.get("arrangement_clip_count") == after.get("arrangement_clip_count")
    )
    effects_unchanged = [device.get("name") for device in before_effects] == [
        device.get("name") for device in after_effects
    ]
    matches = [
        device for device in after.get("devices") or []
        if str(device.get("name") or "").casefold() == device_name.casefold()
    ]
    problems = []
    if len(matches) != 1:
        problems.append(f"Expected one {device_name} device.")
    if len(after_instruments) != 1:
        if len(after_instruments) > 1:
            problems.append("Live left more than one instrument on the track.")
        else:
            problems.append("No instrument remained on the track.")
    if not effects_unchanged:
        problems.append("Audio or MIDI effects changed.")
    if not clips_unchanged:
        problems.append("Clips changed.")
    return {
        "loaded": not problems,
        "error": " ".join(problems),
        "device_index": matches[0].get("index") if len(matches) == 1 else None,
        "replaced_instrument": before_instruments[0].get("name") if before_instruments else None,
        "clips_unchanged": clips_unchanged,
        "effects_unchanged": effects_unchanged,
        "devices": after.get("devices") or [],
    }


def load_configured_preset(
    *,
    plugin_id: str,
    source_path: str,
    connection,
    track_index: int | None = None,
    track_name: str | None = None,
    host_preset_template: str | None = None,
    config_path=None,
    attempts: int = 4,
    pause_seconds: float = 0.4,
) -> dict:
    config = load_user_config(config_path)
    plugin = require_plugin(config, plugin_id)
    source = Path(source_path).expanduser().resolve(strict=True)
    template_value = host_preset_template or plugin["host_preset_template"]
    template = Path(template_value).expanduser().resolve(strict=True)
    payload, report = pack_plugin_preset(plugin_id, source, template)
    before = _prepare_track(connection, track_index, track_name, report.get("preset_name"))
    output = publish_new_bytes(
        Path(plugin["generated_presets_path"]),
        report.get("preset_name") or source.stem,
        payload,
        {source.resolve(), template.resolve()},
    )
    browser_path = plugin["browser_path"]
    uri = _find_uri(connection, browser_path, output, attempts, pause_seconds)
    result = {
        "plugin_id": plugin_id,
        "loaded": False,
        "output_path": str(output),
        "output_sha256": codec.digest(payload),
        "output_bytes": len(payload),
        "source_path": str(source),
        "source_sha256": report.get("source_sha256"),
        "template_path": str(template),
        "template_sha256": report.get("template_sha256"),
        "version": report.get("version"),
        "browser_path": browser_path,
        "browser_uri": uri,
        "track_index": before.get("index"),
        "track_name": before.get("name"),
        "device_name": plugin["device_name"],
        "state_verified": [],
        "limits": LIMITS,
    }
    if not uri:
        result["error"] = (
            "Live has not indexed the new preset. The file is saved; "
            f"browser path {browser_path} did not list it."
        )
        return result
    connection.send_command(
        "load_browser_item",
        {"track_index": before["index"], "item_uri": uri},
    )
    after = _snapshot(connection, before["index"])
    verified = _verify(before, after, plugin["device_name"])
    result.update({key: value for key, value in verified.items() if key != "error"})
    if not result["loaded"]:
        result["error"] = verified["error"]
    if result["loaded"] and result.get("device_index") is not None:
        try:
            parameters = connection.send_command("get_device_parameters", {
                "track_index": before["index"],
                "device_index": result["device_index"],
            })
            result["configure_parameter_count"] = len(parameters.get("parameters") or [])
        except Exception as exc:
            result["configure_parameter_count"] = None
            result["parameter_read_error"] = str(exc)
    elif not result["loaded"] and "error" not in result:
        result["error"] = verified["error"]
    return result
