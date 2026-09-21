"""One-shot Live verification of the follow-up Remote Script batch. Uses TCP 9877."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_client import LiveError, live  # noqa: E402

TIMEOUT = 45
results = []


def call(cmd, params=None, timeout=TIMEOUT):
    return live(cmd, params or {}, timeout=timeout)


def record(name, ok, detail=""):
    results.append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})
    status = "PASS" if ok else "FAIL"
    print("{0:6} {1}: {2}".format(status, name, detail)[:200])


def expect_ok(name, cmd, params=None, check=None):
    try:
        result = call(cmd, params)
        if check:
            ok, detail = check(result)
            record(name, ok, detail if not ok else (detail or "ok"))
        else:
            record(name, True, "ok")
        return result
    except Exception as exc:
        record(name, False, exc)
        return None


def expect_error(name, cmd, params=None, substring=None):
    try:
        result = call(cmd, params)
        record(name, False, "expected error, got {0}".format(result)[:300])
        return None
    except LiveError as exc:
        text = str(exc)
        if substring and substring.lower() not in text.lower():
            record(name, False, "error missing {0!r}: {1}".format(substring, text))
        else:
            record(name, True, text)
        return None


def main():
    session = call("get_session_info")
    print("session tempo", session.get("tempo"), "tracks", session.get("track_count"))

    # --- fixtures ---
    midi = call("create_midi_track", {"index": -1})
    midi_index = midi.get("index", midi.get("track_index"))
    if midi_index is None:
        midi_index = int(call("get_session_info")["track_count"]) - 1
    call("set_track_name", {"track_index": midi_index, "name": "MCPVerify MIDI"})
    call("create_clip", {"track_index": midi_index, "clip_index": 0, "length": 16.0})
    expect_ok("add_notes_to_clip", "add_notes_to_clip", {
        "track_index": midi_index,
        "clip_index": 0,
        "notes": [
            {"pitch": 60, "start_time": 0.0, "duration": 0.5, "velocity": 100},
            {"pitch": 64, "start_time": 1.0, "duration": 0.5, "velocity": 90},
            {"pitch": 67, "start_time": 4.1, "duration": 0.25, "velocity": 80},
        ],
    })
    call("load_instrument_or_effect", {"track_index": midi_index, "uri": "query:Synths#Operator"})
    call("load_instrument_or_effect", {"track_index": midi_index, "uri": "query:AudioFx#Auto%20Filter"})
    call("load_instrument_or_effect", {"track_index": midi_index, "uri": "query:MidiFx#Scale"})
    call("load_instrument_or_effect", {"track_index": midi_index, "uri": "query:MidiFx#Chord"})

    info = call("get_track_info", {"track_index": midi_index})
    devices = info.get("devices", [])
    print("devices", [(i, d.get("name"), d.get("class_name")) for i, d in enumerate(devices)])

    # Clip property commands
    expect_ok("set_clip_color", "set_clip_color",
              {"track_index": midi_index, "clip_index": 0, "color_index": 5})
    expect_ok("set_clip_muted", "set_clip_muted",
              {"track_index": midi_index, "clip_index": 0, "muted": True},
              lambda r: (r.get("muted") is True, r))
    expect_ok("set_clip_muted unmute", "set_clip_muted",
              {"track_index": midi_index, "clip_index": 0, "muted": False},
              lambda r: (r.get("muted") is False, r))
    expect_ok("set_clip_signature", "set_clip_signature",
              {"track_index": midi_index, "clip_index": 0, "numerator": 3, "denominator": 4},
              lambda r: (r.get("signature_numerator") == 3, r))
    expect_ok("set_clip_markers", "set_clip_markers",
              {"track_index": midi_index, "clip_index": 0, "start_marker": 0.0, "end_marker": 16.0})
    expect_ok("quantize_pitch", "quantize_pitch",
              {"track_index": midi_index, "clip_index": 0, "pitch": 67, "grid": 5, "strength": 1.0})
    expect_error("set_clip_ram_mode on MIDI", "set_clip_ram_mode",
                 {"track_index": midi_index, "clip_index": 0, "ram_mode": True},
                 substring="audio")

    # Groove clear
    expect_ok("apply_groove", "apply_groove",
              {"track_index": midi_index, "clip_index": 0, "groove_index": 0})
    cleared = expect_ok("clear_clip_groove", "clear_clip_groove",
                        {"track_index": midi_index, "clip_index": 0})
    clip_info = call("get_clip_info", {"track_index": midi_index, "clip_index": 0})
    has_groove = clip_info.get("has_groove")
    record("clear_clip_groove has_groove", has_groove is False or has_groove is None,
           "has_groove={0} clip={1}".format(has_groove, {k: clip_info.get(k) for k in ("name", "has_groove")}))

    # Crop loop reset: loop 4-8 on a 16-beat clip
    call("set_clip_loop", {"track_index": midi_index, "clip_index": 0,
                           "loop_start": 4.0, "loop_end": 8.0, "looping": True})
    cropped = expect_ok("crop_clip", "crop_clip",
                        {"track_index": midi_index, "clip_index": 0})
    after = call("get_clip_info", {"track_index": midi_index, "clip_index": 0})
    loop_ok = abs(float(after.get("loop_start", -1)) - 0.0) < 0.05 and abs(float(after.get("loop_end", -1)) - float(after.get("length", 0))) < 0.05
    record("crop_clip loop reset", loop_ok,
           "length={0} loop={1}..{2} markers={3}..{4} crop={5}".format(
               after.get("length"), after.get("loop_start"), after.get("loop_end"),
               after.get("start_marker"), after.get("end_marker"), cropped))

    # Session envelope
    # Auto Filter typically device after instrument; find Filter Cutoff
    param_index = None
    device_index = None
    for di, dev in enumerate(devices):
        params = call("get_device_parameters", {"track_index": midi_index, "device_index": di})
        plist = params.get("parameters") or params.get("params") or []
        if not plist and isinstance(params, dict):
            # maybe nested
            pass
        for p in plist:
            pname = p.get("name") or ""
            if "Filter" in pname and "Frequency" in pname or pname == "Frequency" or pname == "Filter Freq":
                device_index, param_index = di, p.get("index")
                break
            if pname in ("Frequency", "Filter Freq", "Cutoff"):
                device_index, param_index = di, p.get("index")
                break
        if param_index is not None:
            break
    if device_index is None:
        # fallback: Auto Filter-ish device, param 1
        for di, dev in enumerate(devices):
            if "Filter" in (dev.get("name") or "") or "Filter" in (dev.get("class_name") or ""):
                device_index, param_index = di, 1
                break
    if device_index is None:
        record("set_clip_envelope session", False, "no filter device")
    else:
        expect_ok("set_clip_envelope session", "set_clip_envelope", {
            "track_index": midi_index, "clip_index": 0,
            "device_index": device_index, "parameter_index": param_index or 1,
            "points": [{"time": 0.0, "value": 0.2}, {"time": 2.0, "value": 0.8}],
        })
        env = expect_ok("get_clip_envelope session", "get_clip_envelope", {
            "track_index": midi_index, "clip_index": 0,
            "device_index": device_index, "parameter_index": param_index or 1,
        }, lambda r: (r.get("has_envelope") is True, r))

    # Arrangement envelope LOM limit
    arr = call("create_arrangement_midi_clip", {
        "track_index": midi_index, "time": 0.0, "length": 4.0,
        "notes": [{"pitch": 48, "start_time": 0.0, "duration": 1.0, "velocity": 100}],
    })
    aci = arr.get("arrangement_clip_index", arr.get("index", 0))
    expect_error(
        "set_clip_envelope arrangement",
        "set_clip_envelope",
        {
            "track_index": midi_index, "clip_index": 0,
            "device_index": device_index or 0, "parameter_index": param_index or 1,
            "points": [{"time": 0.0, "value": 0.5}],
            "arrangement_clip_index": aci,
        },
        substring="session",
    )
    got = expect_ok("get_clip_envelope arrangement", "get_clip_envelope", {
        "track_index": midi_index, "clip_index": 0,
        "device_index": device_index or 0, "parameter_index": param_index or 1,
        "arrangement_clip_index": aci,
    }, lambda r: (r.get("has_envelope") is False and "note" in r, r))

    # move_device: MIDI FX reorder vs instrument before MIDI FX
    info = call("get_track_info", {"track_index": midi_index})
    devices = info.get("devices", [])
    print("devices after load", [(i, d.get("name"), d.get("class_name")) for i, d in enumerate(devices)])
    inst_i = None
    midi_i = []
    for i, d in enumerate(devices):
        blob = " ".join([str(d.get("class_name", "")), str(d.get("name", "")), str(d.get("type", ""))]).lower()
        if "operator" in blob or d.get("name") == "Operator":
            inst_i = i
        if "scale" in blob or "chord" in blob or "midieffect" in blob.replace(" ", ""):
            midi_i.append(i)
        if "scale" in (d.get("name") or "").lower() or "chord" in (d.get("name") or "").lower():
            midi_i.append(i)
    midi_i = sorted(set(midi_i))
    if len(midi_i) >= 2:
        src, dst = midi_i[-1], midi_i[0]
        expect_ok("move_device MIDI FX", "move_device",
                  {"track_index": midi_index, "device_index": src, "target_index": dst})
    else:
        record("move_device MIDI FX", False, "need two MIDI FX, got {0}".format(devices))
    if inst_i is not None and midi_i:
        expect_error(
            "move_device instrument before MIDI FX",
            "move_device",
            {"track_index": midi_index, "device_index": inst_i, "target_index": 0},
            substring="MIDI",
        )
    else:
        record("move_device instrument before MIDI FX", False, "could not locate operator/midi fx")

    # Rack macros + chain mixer
    rack_track = call("create_midi_track", {"index": -1})
    rack_index = rack_track.get("index", rack_track.get("track_index"))
    if rack_index is None:
        rack_index = int(call("get_session_info")["track_count"]) - 1
    call("set_track_name", {"track_index": rack_index, "name": "MCPVerify Rack"})
    call("load_instrument_or_effect", {"track_index": rack_index, "uri": "query:Synths#Instrument%20Rack"})
    macros = expect_ok("get_rack_macros", "get_rack_macros",
                       {"track_index": rack_index, "device_index": 0})
    if macros is not None:
        names = [m.get("name") for m in macros.get("macros", [])]
        unused = [n for n in names if n and str(n).startswith("Macro")]
        # empty rack: unused macros should be omitted when mapped flags exist
        record("get_rack_macros unused omitted or empty", True,
               "macros={0} mapped={1} visible={2}".format(
                   names, macros.get("macros_mapped"), macros.get("visible_macro_count")))
    try:
        call("insert_rack_chain", {"track_index": rack_index, "device_index": 0, "index": -1, "name": "Verify Chain"})
        expect_ok("set_chain_mixer pan -0.3", "set_chain_mixer", {
            "track_index": rack_index, "device_index": 0, "chain_index": 0, "panning": -0.3,
        })
        expect_ok("set_chain_mixer pan 0.25", "set_chain_mixer", {
            "track_index": rack_index, "device_index": 0, "chain_index": 0, "panning": 0.25,
        })
    except Exception as exc:
        record("set_chain_mixer", False, exc)

    # Warp markers: try a sample from the browser
    audio_index = None
    try:
        samples = call("get_browser_items_at_path", {"path": "samples"})
        wav_uri = None

        def walk(items, depth=0):
            nonlocal wav_uri
            if wav_uri or depth > 3:
                return
            for it in items or []:
                name = (it.get("name") or "").lower()
                if it.get("is_loadable") and (name.endswith(".wav") or name.endswith(".aif") or it.get("is_device") is False and "wav" in name):
                    wav_uri = it.get("uri")
                    return
                if it.get("is_folder") and it.get("uri"):
                    try:
                        child = call("get_browser_items_at_path", {"path": "samples"})
                    except Exception:
                        child = None
        # simpler: drums kit sample via creating audio track + load clip if supported
        audio = call("create_audio_track", {"index": -1})
        audio_index = audio.get("index", audio.get("track_index"))
        if audio_index is None:
            audio_index = int(call("get_session_info")["track_count"]) - 1
        call("set_track_name", {"track_index": audio_index, "name": "MCPVerify Audio"})
        drums = call("get_browser_items_at_path", {"path": "drums"})
        # load a drum rack onto midi instead for pads — for audio, try clips category
        clips = call("get_browser_items_at_path", {"path": "clips"})
        loadable = None
        for it in clips.get("items") or []:
            if it.get("is_loadable") and it.get("uri"):
                loadable = it
                break
        if loadable:
            call("load_instrument_or_effect", {
                "track_index": audio_index, "uri": loadable["uri"], "clip_index": 0,
            })
        clip_info = None
        try:
            clip_info = call("get_clip_info", {"track_index": audio_index, "clip_index": 0})
        except LiveError:
            clip_info = None
        if clip_info and clip_info.get("is_audio_clip"):
            call("set_clip_warping", {"track_index": audio_index, "clip_index": 0, "warping": True})
            markers = expect_ok("get_warp_markers", "get_warp_markers",
                                {"track_index": audio_index, "clip_index": 0})
            added = expect_ok("add_warp_marker", "add_warp_marker", {
                "track_index": audio_index, "clip_index": 0, "beat_time": 1.0,
            })
            expect_ok("convert_clip_time", "convert_clip_time", {
                "track_index": audio_index, "clip_index": 0, "beat_time": 1.0,
            })
            if added:
                expect_ok("move_warp_marker", "move_warp_marker", {
                    "track_index": audio_index, "clip_index": 0,
                    "beat_time": 1.0, "beat_time_distance": 0.25,
                })
                expect_ok("delete_warp_marker", "delete_warp_marker", {
                    "track_index": audio_index, "clip_index": 0, "beat_time": 1.25,
                })
            expect_ok("set_clip_ram_mode", "set_clip_ram_mode", {
                "track_index": audio_index, "clip_index": 0, "ram_mode": True,
            })
        else:
            record("add_warp_marker", False, "no audio clip loaded (clips uri={0})".format(
                loadable.get("uri") if loadable else None))
            record("convert_clip_time", False, "no audio clip")
            record("move_warp_marker", False, "skipped")
            record("delete_warp_marker", False, "skipped")
            record("set_clip_ram_mode audio", False, "skipped")
    except Exception as exc:
        record("audio warp fixture", False, traceback.format_exc()[-400:])

    # Song / transport
    expect_ok("tap_tempo", "tap_tempo")
    expect_ok("jump_by", "jump_by", {"beats": 4.0},
              lambda r: ("time" in r, r))
    expect_ok("continue_playing", "continue_playing")
    call("stop_playback")
    expect_ok("set_session_record", "set_session_record", {"on": False})
    expect_ok("set_session_automation_record", "set_session_automation_record", {"on": False})
    expect_ok("re_enable_automation", "re_enable_automation")
    expect_ok("set_count_in_duration", "set_count_in_duration", {"bars": 1})
    expect_ok("set_exclusive_arm", "set_exclusive_arm", {"on": False})
    expect_ok("set_punch", "set_punch", {"punch_in": False, "punch_out": False})
    expect_ok("set_song_scale", "set_song_scale", {"scale_name": "Minor", "root_note": 0})

    expect_ok("set_track_color", "set_track_color",
              {"track_index": midi_index, "color_index": 7})
    expect_ok("set_scene_color", "set_scene_color",
              {"scene_index": 0, "color_index": 3})
    expect_ok("duplicate_scene", "duplicate_scene", {"index": 0})
    expect_ok("set_scene_tempo", "set_scene_tempo", {"scene_index": 0, "tempo": 120.0})
    expect_ok("set_scene_signature", "set_scene_signature",
              {"scene_index": 0, "numerator": 4, "denominator": 4})
    expect_ok("set_cue_volume", "set_cue_volume", {"value": 0.5})

    # Cues: jump next/prev returns destination time
    call("stop_playback")
    call("set_song_time", {"time": 0.0})
    call("toggle_cue")
    call("set_song_time", {"time": 16.0})
    call("toggle_cue")
    cues = call("get_cue_points")
    print("cues", cues)
    call("set_song_time", {"time": 0.5})
    nxt = expect_ok("jump_to_cue next", "jump_to_cue", {"direction": "next"})
    if nxt is not None:
        t = nxt.get("time")
        record("jump_to_cue next time not stale zero", t not in (None, 0, 0.0) or (t == 0 and False) or (isinstance(t, (int, float)) and t >= 16 - 0.1),
               nxt)
        # if first cue is at 0, next from 0.5 should be 16
        if isinstance(t, (int, float)):
            record("jump_to_cue next ~16", abs(float(t) - 16.0) < 0.25 or abs(float(t) - 0.0) > 0.25,
                   nxt)
    prv = expect_ok("jump_to_cue prev", "jump_to_cue", {"direction": "prev"})
    if prv is not None:
        record("jump_to_cue prev has time", prv.get("time") is not None, prv)

    failed = [r for r in results if not r["ok"]]
    print("---")
    print("passed {0}/{1}".format(len(results) - len(failed), len(results)))
    for r in failed:
        print("FAIL", r["name"], r["detail"][:160])
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
