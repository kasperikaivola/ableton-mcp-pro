"""Focused, reversible smoke check for the high-impact Live LOM batch.

Run from the repository root with:
    uv run python tools/_verify_lom_batch_live.py

Optional rack/Simpler checks use only the disposable track created here. This
script deliberately never presses a Live dialog button.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from live_client import LiveError, live, track_by_name


def _last_device_index(track_index: int) -> int:
    devices = live("get_track_info", {"track_index": track_index}).get("devices", [])
    if not devices:
        raise LiveError("device insertion returned no device on the temporary track")
    return len(devices) - 1


def _verify_note_patch(track_index: int) -> None:
    live("create_clip", {"track_index": track_index, "clip_index": 0, "length": 4.0})
    live("add_notes_to_clip", {
        "track_index": track_index,
        "clip_index": 0,
        "notes": [{"pitch": 60, "start_time": 0.0, "duration": 1.0, "velocity": 80}],
    })
    notes = live("get_clip_notes", {"track_index": track_index, "clip_index": 0}).get("notes", [])
    if len(notes) != 1 or notes[0].get("note_id") is None:
        raise LiveError("get_clip_notes did not return the new note_id")

    note_id = notes[0]["note_id"]
    live("apply_note_modifications", {
        "track_index": track_index,
        "clip_index": 0,
        "notes": [{"note_id": note_id, "velocity": 96, "probability": 0.75}],
    })
    updated = live("get_clip_notes", {"track_index": track_index, "clip_index": 0}).get("notes", [])
    changed = next((note for note in updated if note.get("note_id") == note_id), None)
    if changed is None or int(changed.get("velocity")) != 96:
        raise LiveError("note velocity did not round-trip through apply_note_modifications")
    if abs(float(changed.get("probability")) - 0.75) > 1e-6:
        raise LiveError("note probability did not round-trip through apply_note_modifications")
    print("note patch/readback: OK")


def _verify_arrangement_copy(track_index: int) -> None:
    destination_time = 16.0
    live("duplicate_clip_to_arrangement", {
        "track_index": track_index,
        "clip_index": 0,
        "destination_time": destination_time,
    })
    clips = live("get_arrangement_clips", {"track_index": track_index}).get("clips", [])
    if not any(abs(float(clip.get("start_time", -1)) - destination_time) < 1e-6 for clip in clips):
        raise LiveError("duplicate_clip_to_arrangement produced no clip at destination_time")
    print("session-to-arrangement copy: OK")


def _optional_rack_check(track_index: int, enabled: bool) -> None:
    if not enabled:
        print("rack check: skipped (pass --check-rack to use the disposable track)")
        return
    try:
        live("insert_device", {"track_index": track_index, "device_name": "Instrument Rack"})
        device_index = _last_device_index(track_index)
        state = live("get_rack_macros", {"track_index": track_index, "device_index": device_index})
        print("rack check: OK", json.dumps(state, sort_keys=True))
    except LiveError as exc:
        print(f"rack check: skipped ({exc})")


def _optional_simpler_check(track_index: int, sample_path: str | None) -> None:
    if not sample_path:
        print("Simpler check: skipped (no disposable sample path; pass --sample-path)")
        return
    path = Path(sample_path).expanduser().resolve()
    if not path.is_file():
        print(f"Simpler check: skipped (sample path is not a file: {path})")
        return
    try:
        live("insert_device", {"track_index": track_index, "device_name": "Simpler"})
        device_index = _last_device_index(track_index)
        live("replace_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
            "file_path": str(path),
        })
        sample = live("get_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
        })
        sample_length = int(sample.get("sample_length", 0) or 0)
        if sample_length > 1:
            live("set_simpler_sample_window", {
                "track_index": track_index,
                "device_index": device_index,
                "start_marker": 0,
                "end_marker": sample_length,
            })
        print("Simpler check: OK")
    except LiveError as exc:
        print(f"Simpler check: skipped (Live 12.4+ and a supported sample are required: {exc})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-rack", action="store_true")
    parser.add_argument("--sample-path", help="absolute or relative disposable sample for Simpler")
    args = parser.parse_args()

    temporary_name = f"MCP LOM smoke {os.getpid()}-{int(time.time())}"
    temporary_index: int | None = None
    try:
        print("application:", json.dumps(live("get_application_info"), sort_keys=True))
        created = live("create_midi_track", {"index": -1})
        temporary_index = int(created["index"])
        live("set_track_name", {"track_index": temporary_index, "name": temporary_name})
        live("insert_device", {"track_index": temporary_index, "device_name": "Operator"})
        print("native Operator insertion: OK")
        _verify_note_patch(temporary_index)
        _verify_arrangement_copy(temporary_index)
        _optional_rack_check(temporary_index, args.check_rack)
        _optional_simpler_check(temporary_index, args.sample_path)
        print("LOM batch smoke check: PASS")
        return 0
    except LiveError as exc:
        print(f"LOM batch smoke check: FAIL ({exc})", file=sys.stderr)
        return 1
    finally:
        if temporary_index is not None:
            try:
                current_index = track_by_name(temporary_name)
                if current_index is None:
                    print("cleanup: temporary track was not found", file=sys.stderr)
                else:
                    live("delete_track", {"track_index": current_index})
                    print("cleanup: temporary track deleted")
            except LiveError as exc:
                print(f"cleanup: could not delete temporary track ({exc})", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
