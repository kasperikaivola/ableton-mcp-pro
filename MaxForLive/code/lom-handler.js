// lom-handler.js — Max JS (ES5) LiveAPI command handler for AbletonMCP
// Runs inside Max's js object. All LiveAPI calls happen here.

autowatch = 1;
var HANDLER_VERSION = "2026-09-20.3";
inlets = 1;
outlets = 1;

// Command queue — process one at a time
var commandQueue = [];
var processing = false;

// ─── Inlet handler ───
// Receives: command <requestId> <jsonString>

function command() {
    // Collect all arguments — requestId is first, rest is JSON string (may be split by spaces)
    var args = arrayfromargs(messagename, arguments);
    // args[0] = "command", args[1] = requestId, args[2..] = JSON string parts
    var requestId = String(args[1]);
    var jsonStr = args.slice(2).join(" ");

    commandQueue.push({ requestId: requestId, jsonStr: jsonStr });
    if (!processing) {
        processNext();
    }
}

function processNext() {
    if (commandQueue.length === 0) {
        processing = false;
        return;
    }
    processing = true;
    var item = commandQueue.shift();
    var requestId = item.requestId;

    var cmdType = "";
    var params = {};
    try {
        var parsed = JSON.parse(item.jsonStr);
        cmdType = parsed.type || "";
        params = parsed.params || {};
    } catch (e) {
        post("Error parsing command JSON: " + e + "\n");
    }

    var result;
    try {
        result = dispatch(String(cmdType), params);
    } catch (e) {
        finishCommand(requestId, null, e);
        return;
    }

    if (result && result.__deferred === true) {
        // Long-running command: it will call resolve/reject later (from a Task).
        // The queue stays blocked until then so commands run strictly in order.
        result.start(
            function (value) { finishCommand(requestId, value, null); },
            function (err) { finishCommand(requestId, null, err); }
        );
        return;
    }

    finishCommand(requestId, result, null);
}

function finishCommand(requestId, result, err) {
    var responseJson;
    if (err !== null && err !== undefined) {
        responseJson = JSON.stringify({ status: "error", message: String(err) });
    } else {
        responseJson = JSON.stringify({ status: "success", result: result });
    }
    outlet(0, "response", requestId, responseJson);

    // Process next command on next tick to avoid stack overflow
    var t = new Task(processNext);
    t.schedule(1);
}

// Wrap a long-running operation. `starter(resolve, reject)` must eventually call one of them.
function deferred(starter) {
    return { __deferred: true, start: starter };
}

// Handle anything function — catch messages that aren't "command"
function anything() {
    // ignore
}

// ─── Track path resolution ───

function getTrackPath(trackIndex) {
    if (trackIndex === -1) return "live_set master_track";
    if (trackIndex <= -2) return "live_set return_tracks " + (-(trackIndex + 2));
    return "live_set tracks " + trackIndex;
}

function getTrack(trackIndex) {
    return new LiveAPI(getTrackPath(trackIndex));
}

function sessionClipPath(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var aci = param(params, "arrangement_clip_index", null);
    var trackPath = getTrackPath(trackIndex);
    if (aci !== null && aci !== undefined) {
        var count = apiGetOptionalCount(trackPath, "arrangement_clips");
        if (aci < 0 || aci >= count) throw "Arrangement clip index out of range";
        return trackPath + " arrangement_clips " + aci;
    }
    var slotPath = trackPath + " clip_slots " + clipIndex;
    if (!apiGetOptionalNum(slotPath, "has_clip")) throw "No clip in slot";
    return slotPath + " clip";
}

// ─── Command dispatch ───

function dispatch(cmdType, params) {
    switch (cmdType) {
        // Read commands
        case "ping": return { backend: "m4l", handler_version: HANDLER_VERSION, live_version: liveVersion() };
        case "get_session_info": return cmd_get_session_info(params);
        case "get_track_info": return cmd_get_track_info(params);
        case "get_device_parameters": return cmd_get_device_parameters(params);
        case "get_arrangement_info": return cmd_get_arrangement_info(params);
        case "get_arrangement_clips": return cmd_get_arrangement_clips(params);
        case "get_full_arrangement": return cmd_get_full_arrangement(params);
        case "get_clip_notes": return cmd_get_clip_notes(params);
        case "get_arrangement_clip_notes": return cmd_get_arrangement_clip_notes(params);
        case "get_track_routing": return cmd_get_track_routing(params);
        case "get_clip_envelope": return cmd_get_clip_envelope(params);
        case "get_groove_pool": return cmd_get_groove_pool(params);
        case "get_device_sidechain": return cmd_get_device_sidechain(params);
        case "get_rack_chains": return cmd_get_rack_chains(params);
        case "get_rack_macros": return cmd_get_rack_macros(params);
        case "get_simpler_sample": return cmd_get_simpler_sample(params);
        case "get_application_info": return cmd_get_application_info(params);
        case "get_cue_points": return cmd_get_cue_points(params);
        case "get_warp_markers": return cmd_get_warp_markers(params);
        case "get_browser_tree": return cmd_get_browser_tree(params);
        case "get_browser_items_at_path": return cmd_get_browser_items_at_path(params);

        // Simple write commands
        case "set_tempo": return cmd_set_tempo(params);
        case "set_time_signature": return cmd_set_time_signature(params);
        case "set_metronome": return cmd_set_metronome(params);
        case "set_track_name": return cmd_set_track_name(params);
        case "set_track_volume": return cmd_set_track_volume(params);
        case "set_track_panning": return cmd_set_track_panning(params);
        case "set_track_color": return cmd_set_track_color(params);
        case "set_track_mute": return cmd_set_track_mute(params);
        case "set_track_solo": return cmd_set_track_solo(params);
        case "set_track_arm": return cmd_set_track_arm(params);
        case "set_send_level": return cmd_set_send_level(params);
        case "set_crossfader": return cmd_set_crossfader(params);
        case "set_cue_volume": return cmd_set_cue_volume(params);
        case "set_crossfade_assign": return cmd_set_crossfade_assign(params);
        case "set_groove_amount": return cmd_set_groove_amount(params);
        case "set_track_monitoring": return cmd_set_track_monitoring(params);
        case "set_track_input_routing": return cmd_set_track_input_routing(params);
        case "set_track_output_routing": return cmd_set_track_output_routing(params);
        case "start_playback": return cmd_start_playback(params);
        case "stop_playback": return cmd_stop_playback(params);
        case "play_arrangement": return cmd_play_arrangement(params);
        case "set_song_time": return cmd_set_song_time(params);
        case "set_record_mode": return cmd_set_record_mode(params);
        case "capture_midi": return cmd_capture_midi(params);
        case "capture_and_insert_scene": return cmd_capture_and_insert_scene(params);
        case "toggle_cue": return cmd_toggle_cue(params);
        case "jump_to_cue": return cmd_jump_to_cue(params);
        case "tap_tempo": return cmd_tap_tempo(params);
        case "jump_by": return cmd_jump_by(params);
        case "continue_playing": return cmd_continue_playing(params);
        case "set_session_record": return cmd_set_session_record(params);
        case "set_session_automation_record": return cmd_set_session_automation_record(params);
        case "re_enable_automation": return cmd_re_enable_automation(params);
        case "set_count_in_duration": return cmd_set_count_in_duration(params);
        case "set_exclusive_arm": return cmd_set_exclusive_arm(params);
        case "set_punch": return cmd_set_punch(params);
        case "set_song_scale": return cmd_set_song_scale(params);
        case "show_view": return cmd_show_view(params);
        case "set_arrangement_overdub": return cmd_set_arrangement_overdub(params);
        case "set_back_to_arranger": return cmd_set_back_to_arranger(params);
        case "set_arrangement_loop": return cmd_set_arrangement_loop(params);
        case "undo": return cmd_undo(params);
        case "redo": return cmd_redo(params);

        // Track/Scene/Clip management
        case "create_midi_track": return cmd_create_midi_track(params);
        case "create_audio_track": return cmd_create_audio_track(params);
        case "delete_track": return cmd_delete_track(params);
        case "duplicate_track": return cmd_duplicate_track(params);
        case "create_scene": return cmd_create_scene(params);
        case "delete_scene": return cmd_delete_scene(params);
        case "set_scene_name": return cmd_set_scene_name(params);
        case "set_scene_color": return cmd_set_scene_color(params);
        case "duplicate_scene": return cmd_duplicate_scene(params);
        case "set_scene_tempo": return cmd_set_scene_tempo(params);
        case "set_scene_signature": return cmd_set_scene_signature(params);
        case "fire_scene": return cmd_fire_scene(params);
        case "create_clip": return cmd_create_clip(params);
        case "create_audio_clip": return cmd_create_audio_clip(params);
        case "delete_clip": return cmd_delete_clip(params);
        case "duplicate_clip": return cmd_duplicate_clip(params);
        case "set_clip_name": return cmd_set_clip_name(params);
        case "set_clip_loop": return cmd_set_clip_loop(params);
        case "crop_clip": return cmd_crop_clip(params);
        case "set_clip_launch": return cmd_set_clip_launch(params);
        case "set_clip_color": return cmd_set_clip_color(params);
        case "set_clip_muted": return cmd_set_clip_muted(params);
        case "set_clip_markers": return cmd_set_clip_markers(params);
        case "set_clip_signature": return cmd_set_clip_signature(params);
        case "quantize_pitch": return cmd_quantize_pitch(params);
        case "set_clip_ram_mode": return cmd_set_clip_ram_mode(params);
        case "apply_groove": return cmd_apply_groove(params);
        case "clear_clip_groove": return cmd_clear_clip_groove(params);
        case "add_warp_marker": return cmd_add_warp_marker(params);
        case "move_warp_marker": return cmd_move_warp_marker(params);
        case "delete_warp_marker": return cmd_delete_warp_marker(params);
        case "convert_clip_time": return cmd_convert_clip_time(params);
        case "fire_clip": return cmd_fire_clip(params);
        case "stop_clip": return cmd_stop_clip(params);
        case "add_notes_to_clip": return cmd_add_notes_to_clip(params);
        case "apply_note_modifications": return cmd_apply_note_modifications(params);
        case "duplicate_clip_to_arrangement": return cmd_duplicate_clip_to_arrangement(params);
        case "create_arrangement_midi_clip": return cmd_create_arrangement_midi_clip(params);
        case "create_arrangement_audio_clip": return cmd_create_arrangement_audio_clip(params);
        case "delete_arrangement_clip": return cmd_delete_arrangement_clip(params);
        case "record_arrangement": return cmd_record_arrangement(params);

        // Devices, Browser & Automation
        case "set_device_parameter": return cmd_set_device_parameter(params);
        case "batch_set_device_parameters": return cmd_batch_set_device_parameters(params);
        case "set_plugin_preset": return cmd_set_plugin_preset(params);
        case "delete_device": return cmd_delete_device(params);
        case "move_device": return cmd_move_device(params);
        case "set_device_sidechain": return cmd_set_device_sidechain(params);
        case "insert_rack_chain": return cmd_insert_rack_chain(params);
        case "set_chain_mixer": return cmd_set_chain_mixer(params);
        case "add_macro": return cmd_add_macro(params);
        case "remove_macro": return cmd_remove_macro(params);
        case "randomize_macros": return cmd_randomize_macros(params);
        case "store_macro_variation": return cmd_store_macro_variation(params);
        case "recall_macro_variation": return cmd_recall_macro_variation(params);
        case "delete_macro_variation": return cmd_delete_macro_variation(params);
        case "insert_device": return cmd_insert_device(params);
        case "set_simpler_sample_window": return cmd_set_simpler_sample_window(params);
        case "replace_simpler_sample": return cmd_replace_simpler_sample(params);
        case "press_current_dialog_button": return cmd_press_current_dialog_button(params);
        case "load_instrument_or_effect": return cmd_load_instrument_or_effect(params);
        case "load_browser_item": return cmd_load_instrument_or_effect(params);
        case "set_clip_envelope": return cmd_set_clip_envelope(params);
        case "clear_clip_envelope": return cmd_clear_clip_envelope(params);

        default:
            throw "Unknown command: " + cmdType;
    }
}

// ─── Helpers ───

function liveVersion() {
    var app = new LiveAPI("live_app");
    var v = [app.call("get_major_version"), app.call("get_minor_version"), app.call("get_bugfix_version")];
    for (var i = 0; i < v.length; i++) v[i] = (v[i] instanceof Array) ? v[i][0] : v[i];
    return v.join(".");
}

function apiGet(path, prop) {
    var api = new LiveAPI(path);
    return api.get(prop);
}

function apiGetStr(path, prop) {
    var val = apiGet(path, prop);
    if (val instanceof Array) return val.join(" ");
    return String(val);
}

function apiGetNum(path, prop) {
    var val = apiGet(path, prop);
    if (val instanceof Array) return Number(val[0]);
    return Number(val);
}

function apiGetCount(path, child) {
    var api = new LiveAPI(path);
    return api.getcount(child);
}

function apiGetOptionalStr(path, prop) {
    try {
        return apiGetStr(path, prop);
    } catch (e) {
        return null;
    }
}

function apiGetOptionalNum(path, prop) {
    try {
        var value = apiGetNum(path, prop);
        return isFinite(value) ? value : null;
    } catch (e) {
        return null;
    }
}

function apiGetOptionalCount(path, child) {
    try {
        var count = Number(apiGetCount(path, child));
        return isFinite(count) && count > 0 ? Math.floor(count) : 0;
    } catch (e) {
        return 0;
    }
}

function param(params, key, defaultVal) {
    var v = params[key];
    if (v === undefined || v === null) return defaultVal;
    return v;
}

function canonicalPanning(panning) {
    panning = Number(panning);
    if (panning < 0) panning = (panning + 1) / 2;
    if (!isFinite(panning) || panning < 0.0 || panning > 1.0) throw "Panning must be between 0.0 and 1.0";
    return panning;
}

function unwrapNum(raw) {
    if (raw instanceof Array) raw = raw[0];
    return Number(raw);
}

function clipIsArrangement(params, clipPath) {
    var aci = param(params, "arrangement_clip_index", null);
    if (aci !== null && aci !== undefined) return true;
    return apiGetOptionalNum(clipPath, "is_arrangement_clip") ? true : false;
}

function asBoolList(raw) {
    if (raw === null || raw === undefined) return null;
    var items;
    if (raw instanceof Array) {
        items = raw;
    } else if (typeof raw === "string") {
        var s = String(raw).replace(/^\s+|\s+$/g, "");
        if (!s) return null;
        if (s.charAt(0) === "[") {
            try {
                items = JSON.parse(s);
            } catch (e) {
                return null;
            }
        } else {
            items = s.split(/[\s,]+/);
        }
    } else {
        return null;
    }
    if (!items || items.length < 2) return null;
    var out = [];
    var i = 0;
    if (typeof items[0] === "string" && items[0] !== "true" && items[0] !== "false" && isNaN(Number(items[0]))) {
        i = 1;
    }
    for (; i < items.length; i++) {
        var v = items[i];
        if (typeof v === "boolean") {
            out.push(v);
        } else if (v === "true" || v === "false") {
            out.push(v === "true");
        } else {
            var n = Number(v);
            if (!isFinite(n)) return null;
            out.push(n ? true : false);
        }
    }
    return out.length >= 2 ? out : null;
}

function macroNumberFromName(label) {
    if (!label) return null;
    var s = String(label);
    if (s.indexOf("Macro") !== 0) return null;
    var i = 5;
    while (i < s.length && s.charAt(i) === " ") i++;
    if (i >= s.length) return null;
    var n = parseInt(s.substring(i), 10);
    if (!isFinite(n) || n < 1) return null;
    return n;
}

function setColorFields(api, path, params, label) {
    var colorIndex = param(params, "color_index", null);
    var color = param(params, "color", null);
    if (colorIndex === null && color === null) throw "set_" + label + "_color requires color_index and/or color";
    if (colorIndex !== null) {
        try {
            api.set("color_index", Math.floor(Number(colorIndex)));
        } catch (e) {
            throw "color_index is not available on this " + label;
        }
    }
    if (color !== null) {
        try {
            api.set("color", Math.floor(Number(color)));
        } catch (e) {
            throw "color is not available on this " + label;
        }
    }
    var result = {};
    var ci = apiGetOptionalNum(path, "color_index");
    var c = apiGetOptionalNum(path, "color");
    if (ci !== null) result.color_index = ci;
    if (c !== null) result.color = c;
    return result;
}

function jumpToCueIndex(index) {
    var cuePath = "live_set cue_points " + index;
    var cue = new LiveAPI(cuePath);
    if (!cue.id || cue.id === "0") throw "Cue index out of range";
    try {
        cue.call("jump");
    } catch (e) {
        var song = new LiveAPI("live_set");
        song.set("current_song_time", apiGetNum(cuePath, "time"));
    }
    return {
        jumped: true,
        index: index,
        name: apiGetOptionalStr(cuePath, "name"),
        time: apiGetOptionalNum(cuePath, "time")
    };
}

// ─── Read Commands ───

function cmd_get_session_info() {
    var song = new LiveAPI("live_set");
    var tempo = apiGetNum("live_set", "tempo");
    var sigNum = apiGetNum("live_set", "signature_numerator");
    var sigDen = apiGetNum("live_set", "signature_denominator");
    var trackCount = apiGetCount("live_set", "tracks");
    var returnCount = apiGetCount("live_set", "return_tracks");

    var master = new LiveAPI("live_set master_track");
    var masterVol = apiGetNum("live_set master_track mixer_device volume", "value");
    var masterPan = apiGetNum("live_set master_track mixer_device panning", "value");

    return {
        tempo: tempo,
        signature_numerator: sigNum,
        signature_denominator: sigDen,
        track_count: trackCount,
        return_track_count: returnCount,
        master_track: {
            name: "Master",
            volume: masterVol,
            panning: masterPan
        }
    };
}

function cmd_get_track_info(params) {
    var trackIndex = param(params, "track_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);

    if (!track.id || track.id === "0") {
        throw "Track index out of range";
    }

    var name = apiGetStr(trackPath, "name");
    var hasAudioInput = apiGetOptionalNum(trackPath, "has_audio_input");
    var hasMidiInput = apiGetOptionalNum(trackPath, "has_midi_input");
    var mute = apiGetOptionalNum(trackPath, "mute");
    var solo = apiGetOptionalNum(trackPath, "solo");
    var arm = apiGetOptionalNum(trackPath, "arm");
    var volume = apiGetOptionalNum(trackPath + " mixer_device volume", "value");
    var panning = apiGetOptionalNum(trackPath + " mixer_device panning", "value");

    var kind = trackIndex === -1 ? "master" : (trackIndex <= -2 ? "return" : "regular");
    var isFoldable = apiGetOptionalNum(trackPath, "is_foldable");
    var isGrouped = apiGetOptionalNum(trackPath, "is_grouped");
    var explicitGroup = apiGetOptionalNum(trackPath, "is_group_track");
    if (trackIndex >= 0 && (explicitGroup || isFoldable)) kind = "group";

    // Get clip slots
    var slotCount = apiGetOptionalCount(trackPath, "clip_slots");
    var clipSlots = [];
    for (var i = 0; i < slotCount; i++) {
        var slotPath = trackPath + " clip_slots " + i;
        var hasClip = apiGetOptionalNum(slotPath, "has_clip");
        var clipInfo = null;
        if (hasClip) {
            var clipPath = slotPath + " clip";
            clipInfo = {
                name: apiGetOptionalStr(clipPath, "name"),
                length: apiGetOptionalNum(clipPath, "length"),
                is_playing: apiGetOptionalNum(clipPath, "is_playing") ? true : false,
                is_recording: apiGetOptionalNum(clipPath, "is_recording") ? true : false
            };
        }
        clipSlots.push({
            index: i,
            has_clip: hasClip ? true : false,
            clip: clipInfo
        });
    }

    // Get devices
    var deviceCount = apiGetOptionalCount(trackPath, "devices");
    var devices = [];
    for (var d = 0; d < deviceCount; d++) {
        var devPath = trackPath + " devices " + d;
        var devName = apiGetOptionalStr(devPath, "name");
        var className = apiGetOptionalStr(devPath, "class_name");
        var devType = getDeviceType(devPath);
        devices.push({
            index: d,
            name: devName,
            class_name: className,
            type: devType
        });
    }

    var result = {
        index: trackIndex,
        name: name,
        kind: kind,
        track_kind: kind,
        is_group_track: kind === "group",
        clip_slots: clipSlots,
        devices: devices
    };

    if (hasAudioInput !== null) result.is_audio_track = hasAudioInput ? true : false;
    if (hasMidiInput !== null) result.is_midi_track = hasMidiInput ? true : false;
    if (mute !== null) result.mute = mute ? true : false;
    if (solo !== null) result.solo = solo ? true : false;
    if (arm !== null) result.arm = arm ? true : false;
    if (volume !== null) result.volume = volume;
    if (panning !== null) result.panning = panning;
    if (isFoldable !== null) result.is_foldable = isFoldable ? true : false;
    if (isGrouped !== null) result.is_grouped = isGrouped ? true : false;

    var foldState = apiGetOptionalNum(trackPath, "fold_state");
    if (foldState !== null) result.fold_state = foldState;

    var childCount = apiGetOptionalCount(trackPath, "children");
    if (childCount) result.child_track_count = childCount;

    var groupTrackPath = trackPath + " group_track";
    try {
        var groupTrack = new LiveAPI(groupTrackPath);
        if (groupTrack.id && groupTrack.id !== "0") {
            var groupName = apiGetOptionalStr(groupTrackPath, "name");
            result.group_track = {
                id: String(groupTrack.id),
                name: groupName
            };
            if (groupName !== null) result.group_track_name = groupName;
            var trackCount = apiGetOptionalCount("live_set", "tracks");
            for (var gi = 0; gi < trackCount; gi++) {
                try {
                    var candidate = new LiveAPI("live_set tracks " + gi);
                    if (candidate.id && String(candidate.id) === String(groupTrack.id)) {
                        result.group_track_index = gi;
                        break;
                    }
                } catch (lookupErr) {
                    // Skip tracks Live cannot inspect while resolving the parent group.
                }
            }
        }
    } catch (e) {
        // group_track is unavailable on some track types and older Live versions.
    }

    return result;
}

function getDeviceType(devPath) {
    try {
        var canDrumPads = apiGetNum(devPath, "can_have_drum_pads");
        if (canDrumPads) return "drum_machine";
        var canChains = apiGetNum(devPath, "can_have_chains");
        if (canChains) return "rack";
        var className = apiGetStr(devPath, "class_name");
        var lomType = apiGetNum(devPath, "type");
        if (className === "PluginDevice" || className === "AuPluginDevice") {
            if (lomType === 1) return "instrument";
            if (lomType === 2) return "audio_effect";
            if (lomType === 4) return "midi_effect";
            return "plugin";
        }
        var classDisplay = apiGetStr(devPath, "class_display_name");
        if (classDisplay.toLowerCase().indexOf("instrument") >= 0) return "instrument";
        if (className.toLowerCase().indexOf("audio_effect") >= 0) return "audio_effect";
        if (className.toLowerCase().indexOf("midi_effect") >= 0) return "midi_effect";
        if (lomType === 1) return "instrument";
        if (lomType === 2) return "audio_effect";
        if (lomType === 4) return "midi_effect";
        return "unknown";
    } catch (e) {
        return "unknown";
    }
}

function parameterGroup(name) {
    var raw = String(name || "");
    var lower = raw.toLowerCase();
    if (raw.indexOf(">") >= 0) return "Filter routing";
    if (lower === "device on" || lower.indexOf("device on") === 0) return "Device";
    if (lower.indexOf("macro") === 0) return "Macros";
    if (lower.indexOf("noise") === 0) return "Noise";
    if (lower.indexOf("sub") === 0) return "Sub oscillator";
    if (lower.indexOf("main") === 0 || lower === "master vol" || lower === "master volume") return "Main";
    if (lower.indexOf("clip player") === 0 || lower.indexOf("arp") === 0) return "Playback";
    if (lower === "key" || lower === "scale") return "Scale";
    if (lower === "swing") return "Groove";
    if (lower === "pitch bend" || lower === "bend up" || lower === "bend down" ||
        lower === "mod wheel" || lower === "transpose" || lower.indexOf("porta") === 0 ||
        lower === "mono toggle" || lower === "legato" || lower.indexOf("bend ") === 0) {
        return "Voice";
    }
    var parts = raw.split(" ");
    if (parts.length >= 2) {
        var head = parts[0].toLowerCase();
        var second = parts[1];
        if (head === "filter" && /^\d+$/.test(second)) return "Filter " + second;
        if ((head === "env" || head === "envelope") && /^\d+$/.test(second)) return "Envelope " + second;
        if (head === "lfo" && /^\d+$/.test(second)) return "LFO " + second;
    }
    if (parts.length >= 1 && (parts[0] === "A" || parts[0] === "B" || parts[0] === "C")) {
        return "Oscillator " + parts[0];
    }
    return "Other";
}

function attachGroups(parameters) {
    var order = [];
    var buckets = {};
    var i;
    for (i = 0; i < parameters.length; i++) {
        var group = parameters[i].group || parameterGroup(parameters[i].name);
        parameters[i].group = group;
        if (!buckets[group]) {
            order.push(group);
            buckets[group] = [];
        }
        buckets[group].push({ index: parameters[i].index, name: parameters[i].name });
    }
    var groups = [];
    for (i = 0; i < order.length; i++) {
        groups.push({
            name: order[i],
            count: buckets[order[i]].length,
            parameters: buckets[order[i]]
        });
    }
    return groups;
}

function paramQueryMatches(p, query) {
    if (!query) return true;
    var q = String(query).toLowerCase();
    var fields = [p.name, p.original_name, p.display_value, p.group];
    for (var i = 0; i < fields.length; i++) {
        if (fields[i] && String(fields[i]).toLowerCase().indexOf(q) >= 0) return true;
    }
    return false;
}

function findParameterIndex(parameters, parameterIndex, parameterName) {
    if (parameterIndex !== null && parameterIndex !== undefined) {
        if (parameterIndex < 0 || parameterIndex >= parameters.length) throw "Parameter index out of range";
        return parameterIndex;
    }
    if (!parameterName) throw "parameter_index or parameter_name is required";
    var needle = String(parameterName).toLowerCase();
    var exact = [];
    var partial = [];
    var i;
    for (i = 0; i < parameters.length; i++) {
        var n = String(parameters[i].name || "").toLowerCase();
        if (n === needle) exact.push(i);
        else if (n.indexOf(needle) >= 0) partial.push(i);
    }
    if (exact.length === 1) return exact[0];
    if (exact.length > 1) throw "parameter name is ambiguous";
    if (partial.length === 1) return partial[0];
    if (partial.length > 1) throw "parameter name is ambiguous";
    throw "parameter name not found: " + parameterName;
}

function cmd_get_device_parameters(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var query = param(params, "query", null);
    var trackPath = getTrackPath(trackIndex);
    var devPath = trackPath + " devices " + deviceIndex;

    var dev = new LiveAPI(devPath);
    if (!dev.id || dev.id === "0") throw "Device index out of range";

    var trackName = apiGetStr(trackPath, "name");
    var devName = apiGetStr(devPath, "name");
    var className = apiGetStr(devPath, "class_name");
    var paramCount = apiGetCount(devPath, "parameters");
    var parameters = [];
    var i;

    for (i = 0; i < paramCount; i++) {
        var pPath = devPath + " parameters " + i;
        var pName = apiGetStr(pPath, "name");
        var pVal = apiGetNum(pPath, "value");
        var pMin = apiGetNum(pPath, "min");
        var pMax = apiGetNum(pPath, "max");
        var pIsQuant = apiGetNum(pPath, "is_quantized");
        var pIsEnabled = apiGetNum(pPath, "is_enabled");
        var orig = apiGetOptionalStr(pPath, "original_name");
        var display = apiGetOptionalStr(pPath, "display_value");
        var normVal = 0;
        if ((pMax - pMin) !== 0) {
            normVal = (pVal - pMin) / (pMax - pMin);
        }
        parameters.push({
            index: i,
            name: pName,
            original_name: orig,
            value: pVal,
            normalized_value: normVal,
            min: pMin,
            max: pMax,
            is_quantized: pIsQuant ? true : false,
            is_enabled: pIsEnabled ? true : false,
            display_value: display,
            group: parameterGroup(pName)
        });
    }

    var matched = [];
    if (query) {
        var qExact = String(query).toLowerCase();
        for (i = 0; i < parameters.length; i++) {
            if (String(parameters[i].group || "").toLowerCase() === qExact) matched.push(parameters[i]);
        }
    }
    if (!query) {
        matched = parameters;
    } else if (matched.length === 0) {
        for (i = 0; i < parameters.length; i++) {
            if (paramQueryMatches(parameters[i], query)) matched.push(parameters[i]);
        }
    }
    var groups = attachGroups(matched);

    var presets = [];
    try {
        var rawPresets = new LiveAPI(devPath).get("presets");
        if (rawPresets && rawPresets.length) {
            for (i = 0; i < rawPresets.length; i++) {
                if (rawPresets[i] !== "id") presets.push(String(rawPresets[i]));
            }
        }
    } catch (presetErr) {}

    var isPlugin = (className === "PluginDevice" || className === "AuPluginDevice");
    return {
        track_index: trackIndex,
        track_name: trackName,
        device_index: deviceIndex,
        device_name: devName,
        class_name: className,
        type: getDeviceType(devPath),
        is_plugin: isPlugin,
        configured_parameter_count: parameters.length,
        presets: presets,
        selected_preset_index: isPlugin ? apiGetOptionalNum(devPath, "selected_preset_index") : null,
        query: query,
        groups: groups,
        parameters: matched
    };
}

function cmd_get_arrangement_info() {
    return {
        current_song_time: apiGetNum("live_set", "current_song_time"),
        is_playing: apiGetNum("live_set", "is_playing") ? true : false,
        record_mode: apiGetNum("live_set", "record_mode") ? true : false,
        arrangement_overdub: apiGetNum("live_set", "arrangement_overdub") ? true : false,
        back_to_arranger: apiGetNum("live_set", "back_to_arranger") ? true : false,
        loop: apiGetNum("live_set", "loop") ? true : false,
        loop_start: apiGetNum("live_set", "loop_start"),
        loop_length: apiGetNum("live_set", "loop_length"),
        tempo: apiGetNum("live_set", "tempo"),
        scene_count: apiGetCount("live_set", "scenes"),
        song_length: apiGetNum("live_set", "song_length")
    };
}

function arrangementClipInfo(clipPath) {
    var isAudio = apiGetOptionalNum(clipPath, "is_audio_clip") ? true : false;
    var startTime = apiGetOptionalNum(clipPath, "start_time");
    var endTime = apiGetOptionalNum(clipPath, "end_time");
    var length = apiGetOptionalNum(clipPath, "length");
    var info = {
        name: apiGetOptionalStr(clipPath, "name") || "",
        start_time: startTime !== null ? startTime : 0,
        end_time: endTime !== null ? endTime : 0,
        length: length !== null ? length : 0,
        is_midi_clip: apiGetOptionalNum(clipPath, "is_midi_clip") ? true : false,
        is_audio_clip: isAudio
    };
    if (isAudio) {
        var filePath = apiGetOptionalStr(clipPath, "file_path");
        if (filePath !== null) info.file_path = filePath;
    }
    return info;
}

function cmd_get_arrangement_clips(params) {
    var trackIndex = param(params, "track_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var trackName = apiGetOptionalStr(trackPath, "name") || "";

    var clips = [];
    var clipCount = apiGetOptionalCount(trackPath, "arrangement_clips");
    for (var i = 0; i < clipCount; i++) {
        clips.push(arrangementClipInfo(trackPath + " arrangement_clips " + i));
    }

    return {
        track_index: trackIndex,
        track_name: trackName,
        arrangement_clip_count: clips.length,
        clips: clips
    };
}

function cmd_get_full_arrangement() {
    var trackCount = apiGetOptionalCount("live_set", "tracks");
    var tracksData = [];

    for (var i = 0; i < trackCount; i++) {
        var trackPath = "live_set tracks " + i;
        var clipCount = apiGetOptionalCount(trackPath, "arrangement_clips");
        if (clipCount === 0) continue;

        var clips = [];
        for (var c = 0; c < clipCount; c++) {
            clips.push(arrangementClipInfo(trackPath + " arrangement_clips " + c));
        }

        tracksData.push({
            track_index: i,
            track_name: apiGetOptionalStr(trackPath, "name") || "",
            clips: clips
        });
    }

    var sceneCount = apiGetOptionalCount("live_set", "scenes");
    var scenes = [];
    for (var s = 0; s < sceneCount; s++) {
        scenes.push({
            index: s,
            name: apiGetOptionalStr("live_set scenes " + s, "name") || ""
        });
    }

    var tempo = apiGetOptionalNum("live_set", "tempo");
    var sigNum = apiGetOptionalNum("live_set", "signature_numerator");
    var sigDen = apiGetOptionalNum("live_set", "signature_denominator");
    var songLength = apiGetOptionalNum("live_set", "song_length");
    return {
        tempo: tempo !== null ? tempo : 0,
        time_signature: (sigNum !== null ? sigNum : 4) + "/" + (sigDen !== null ? sigDen : 4),
        song_length: songLength !== null ? songLength : 0,
        tracks_with_clips: tracksData,
        scenes: scenes
    };
}

function cmd_get_clip_notes(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var slotPath = trackPath + " clip_slots " + clipIndex;

    var hasClip = apiGetNum(slotPath, "has_clip");
    if (!hasClip) throw "No clip in slot";

    var clipPath = slotPath + " clip";
    var isMidi = apiGetNum(clipPath, "is_midi_clip");
    if (!isMidi) throw "Not a MIDI clip";

    var clipLength = apiGetNum(clipPath, "length");
    var clipName = apiGetStr(clipPath, "name");

    var clip = new LiveAPI(clipPath);
    var noteList = readAllNotes(clip, clipLength);

    return {
        track_index: trackIndex,
        clip_index: clipIndex,
        clip_name: clipName,
        length: clipLength,
        note_count: noteList.length,
        notes: noteList
    };
}

function cmd_get_clip_envelope(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var parameterIndex = param(params, "parameter_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var clipPath = sessionClipPath(params);
    var devPath = trackPath + " devices " + deviceIndex;
    var pPath = devPath + " parameters " + parameterIndex;
    var paramName = apiGetStr(pPath, "name");
    var pMin = apiGetNum(pPath, "min");
    var pMax = apiGetNum(pPath, "max");
    var paramRange = pMax - pMin;

    var clipLength = apiGetNum(clipPath, "length");

    if (clipIsArrangement(params, clipPath)) {
        return {
            track_index: trackIndex,
            clip_index: clipIndex,
            parameter_name: paramName,
            has_envelope: false,
            points: [],
            note: "Arrangement clip envelopes are not in the LOM (session only)"
        };
    }

    // Try to get automation envelope via the clip
    var clip = new LiveAPI(clipPath);
    var paramApi = new LiveAPI(pPath);

    // Use automation_envelope — may return null/0 if no envelope exists
    var envId = clip.call("automation_envelope", "id", paramApi.id);
    if (!envId || envId === "0" || envId === 0) {
        return {
            track_index: trackIndex,
            clip_index: clipIndex,
            parameter_name: paramName,
            has_envelope: false,
            points: []
        };
    }

    // Sample the envelope at regular intervals
    var numSamples = Math.min(Math.floor(clipLength), 64);
    if (numSamples < 1) numSamples = 1;
    var step = clipLength / numSamples;
    var points = [];

    var envApi = new LiveAPI("id " + envId);
    for (var i = 0; i < numSamples; i++) {
        var t = i * step;
        var val = Number(envApi.call("value_at_time", t));
        var normalized = paramRange > 0 ? (val - pMin) / paramRange : 0;
        points.push({
            time: Math.round(t * 1000) / 1000,
            value: Math.round(normalized * 10000) / 10000
        });
    }

    return {
        track_index: trackIndex,
        clip_index: clipIndex,
        parameter_name: paramName,
        has_envelope: true,
        points: points
    };
}

// Browser categories are named properties on the browser object
var BROWSER_CATEGORIES = ["instruments", "sounds", "drums", "audio_effects", "midi_effects"];
var BROWSER_CATEGORY_LABELS = {
    "instruments": "Instruments",
    "sounds": "Sounds",
    "drums": "Drums",
    "audio_effects": "Audio Effects",
    "midi_effects": "MIDI Effects"
};

// Get a LiveAPI for a browser category by name.
// "live_app browser" doesn't work as a path — browser is a property returning an object id.
function getBrowserCategory(catName) {
    // Browser is NOT accessible from M4L's JS LiveAPI.
    // Application.browser is only available from Python Remote Scripts.
    // Returns null — browser commands will return friendly error messages.
    return null;
}

function cmd_get_browser_tree(params) {
    throw "Browser is not accessible from Max for Live devices. Use the Remote Script instead, or drag instruments manually from Ableton's browser.";
}

function cmd_get_browser_items_at_path(params) {
    throw "Browser is not accessible from Max for Live devices. Use the Remote Script instead, or drag instruments manually from Ableton's browser.";
}

// ─── Simple Write Commands ───

function cmd_set_tempo(params) {
    var tempo = param(params, "tempo", 120.0);
    var song = new LiveAPI("live_set");
    song.set("tempo", tempo);
    return { tempo: apiGetNum("live_set", "tempo") };
}

function cmd_set_time_signature(params) {
    var numerator = param(params, "numerator", 4);
    var denominator = param(params, "denominator", 4);
    var song = new LiveAPI("live_set");
    song.set("signature_numerator", Math.floor(numerator));
    song.set("signature_denominator", Math.floor(denominator));
    return {
        numerator: apiGetNum("live_set", "signature_numerator"),
        denominator: apiGetNum("live_set", "signature_denominator")
    };
}

function cmd_set_metronome(params) {
    var on = param(params, "on", false);
    var song = new LiveAPI("live_set");
    song.set("metronome", on ? 1 : 0);
    return { metronome: apiGetNum("live_set", "metronome") ? true : false };
}

function cmd_set_track_name(params) {
    var trackIndex = param(params, "track_index", 0);
    var name = param(params, "name", "");
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    track.set("name", name);
    return { name: apiGetStr(trackPath, "name") };
}

function cmd_set_track_volume(params) {
    var trackIndex = param(params, "track_index", 0);
    var volume = param(params, "volume", 0.85);
    if (volume < 0.0 || volume > 1.0) throw "Volume must be between 0.0 and 1.0";

    var trackPath = getTrackPath(trackIndex);
    var volPath = trackPath + " mixer_device volume";
    var volMin = apiGetNum(volPath, "min");
    var volMax = apiGetNum(volPath, "max");
    var actualValue = volMin + volume * (volMax - volMin);

    var vol = new LiveAPI(volPath);
    vol.set("value", actualValue);

    return {
        track_name: apiGetStr(trackPath, "name"),
        volume: apiGetNum(volPath, "value"),
        normalized_volume: volume
    };
}

function cmd_set_track_panning(params) {
    var trackIndex = param(params, "track_index", 0);
    var panning = canonicalPanning(param(params, "panning", 0.0));

    var trackPath = getTrackPath(trackIndex);
    var panPath = trackPath + " mixer_device panning";
    var panMin = apiGetNum(panPath, "min");
    var panMax = apiGetNum(panPath, "max");
    var actualValue = panMin + panning * (panMax - panMin);

    var pan = new LiveAPI(panPath);
    pan.set("value", actualValue);

    return {
        track_name: apiGetStr(trackPath, "name"),
        panning: apiGetNum(panPath, "value"),
        normalized_panning: panning
    };
}

function cmd_set_track_mute(params) {
    var trackIndex = param(params, "track_index", 0);
    var mute = param(params, "mute", false);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    track.set("mute", mute ? 1 : 0);
    return {
        track_name: apiGetStr(trackPath, "name"),
        mute: apiGetNum(trackPath, "mute") ? true : false
    };
}

function cmd_set_track_solo(params) {
    var trackIndex = param(params, "track_index", 0);
    var solo = param(params, "solo", false);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    track.set("solo", solo ? 1 : 0);
    return {
        track_name: apiGetStr(trackPath, "name"),
        solo: apiGetNum(trackPath, "solo") ? true : false
    };
}

function cmd_set_track_arm(params) {
    var trackIndex = param(params, "track_index", 0);
    var arm = param(params, "arm", false);
    var trackPath = "live_set tracks " + trackIndex;
    var canArm = apiGetNum(trackPath, "can_be_armed");
    if (!canArm) throw "Track cannot be armed";
    var track = new LiveAPI(trackPath);
    track.set("arm", arm ? 1 : 0);
    return {
        track_index: trackIndex,
        track_name: apiGetStr(trackPath, "name"),
        arm: apiGetNum(trackPath, "arm") ? true : false
    };
}

function cmd_set_send_level(params) {
    var trackIndex = param(params, "track_index", 0);
    var sendIndex = param(params, "send_index", 0);
    var value = param(params, "value", 0.0);
    var trackPath = getTrackPath(trackIndex);
    var sendPath = trackPath + " mixer_device sends " + sendIndex;

    var sendApi = new LiveAPI(sendPath);
    if (!sendApi.id || sendApi.id === "0") throw "Send index out of range";

    var sMin = apiGetNum(sendPath, "min");
    var sMax = apiGetNum(sendPath, "max");
    var actualValue = Math.max(sMin, Math.min(sMax, sMin + value * (sMax - sMin)));
    sendApi.set("value", actualValue);

    return {
        track_index: trackIndex,
        send_index: sendIndex,
        value: value,
        actual_value: apiGetNum(sendPath, "value")
    };
}

function cmd_start_playback() {
    var song = new LiveAPI("live_set");
    song.call("start_playing");
    return { playing: apiGetNum("live_set", "is_playing") ? true : false };
}

function cmd_stop_playback() {
    var song = new LiveAPI("live_set");
    song.call("stop_playing");
    return { playing: apiGetNum("live_set", "is_playing") ? true : false };
}

function cmd_play_arrangement(params) {
    var time = param(params, "time", null);
    var song = new LiveAPI("live_set");
    song.call("stop_all_clips");
    song.set("back_to_arranger", 1);
    if (time !== null) {
        song.set("current_song_time", Number(time));
    }
    song.call("start_playing");
    return {
        playing: true,
        position: apiGetNum("live_set", "current_song_time")
    };
}

function cmd_set_song_time(params) {
    var time = param(params, "time", 0.0);
    var target = Math.max(0.0, time);
    var song = new LiveAPI("live_set");
    for (var attempt = 0; attempt < 5; attempt++) {
        song.set("current_song_time", target);
        var actual = apiGetNum("live_set", "current_song_time");
        if (Math.abs(actual - target) < 0.5) break;
    }
    return { current_song_time: apiGetNum("live_set", "current_song_time") };
}

function cmd_set_record_mode(params) {
    var on = param(params, "on", false);
    var song = new LiveAPI("live_set");
    song.set("record_mode", on ? 1 : 0);
    return { record_mode: apiGetNum("live_set", "record_mode") ? true : false };
}

function cmd_capture_midi(params) {
    var raw = param(params, "destination", 0);
    if (typeof raw !== "number" || !isFinite(raw) || Math.floor(raw) !== raw ||
            (raw !== 0 && raw !== 1 && raw !== 2)) {
        throw "destination must be an integer 0, 1, or 2";
    }

    var destinationNames = ["auto", "session", "arrangement"];
    var song = new LiveAPI("live_set");
    song.call("capture_midi", raw);
    return {
        captured: true,
        destination: raw,
        destination_name: destinationNames[raw]
    };
}

function cmd_set_arrangement_overdub(params) {
    var on = param(params, "on", false);
    var song = new LiveAPI("live_set");
    song.set("arrangement_overdub", on ? 1 : 0);
    return { arrangement_overdub: apiGetNum("live_set", "arrangement_overdub") ? true : false };
}

function cmd_set_back_to_arranger() {
    var song = new LiveAPI("live_set");
    song.set("back_to_arranger", 1);
    return { back_to_arranger: true };
}

function cmd_set_arrangement_loop(params) {
    var on = param(params, "on", true);
    var start = param(params, "start", null);
    var length = param(params, "length", null);
    var song = new LiveAPI("live_set");
    song.set("loop", on ? 1 : 0);
    if (start !== null) song.set("loop_start", Math.max(0.0, start));
    if (length !== null) song.set("loop_length", Math.max(0.0, length));
    return {
        loop: apiGetNum("live_set", "loop") ? true : false,
        loop_start: apiGetNum("live_set", "loop_start"),
        loop_length: apiGetNum("live_set", "loop_length")
    };
}

function cmd_undo() {
    var song = new LiveAPI("live_set");
    song.call("undo");
    return { undone: true };
}

function cmd_redo() {
    var song = new LiveAPI("live_set");
    song.call("redo");
    return { redone: true };
}

// ─── Track/Scene/Clip Management ───

function cmd_create_midi_track(params) {
    var index = param(params, "index", -1);
    var song = new LiveAPI("live_set");
    song.call("create_midi_track", index);
    var trackCount = apiGetCount("live_set", "tracks");
    var newIndex = (index === -1) ? trackCount - 1 : index;
    return {
        index: newIndex,
        name: apiGetStr("live_set tracks " + newIndex, "name")
    };
}

function cmd_create_audio_track(params) {
    var index = param(params, "index", -1);
    var song = new LiveAPI("live_set");
    var trackCount = apiGetCount("live_set", "tracks");
    if (index < 0) index = trackCount;
    song.call("create_audio_track", index);
    return {
        index: index,
        name: apiGetStr("live_set tracks " + index, "name"),
        track_count: apiGetCount("live_set", "tracks")
    };
}

function cmd_delete_track(params) {
    var trackIndex = param(params, "track_index", 0);
    var trackName = apiGetStr("live_set tracks " + trackIndex, "name");
    var song = new LiveAPI("live_set");
    song.call("delete_track", trackIndex);
    return {
        deleted_track: trackName,
        track_count: apiGetCount("live_set", "tracks")
    };
}

function cmd_duplicate_track(params) {
    var trackIndex = param(params, "track_index", 0);
    var trackName = apiGetStr("live_set tracks " + trackIndex, "name");
    var song = new LiveAPI("live_set");
    song.call("duplicate_track", trackIndex);
    return {
        original_track: trackName,
        new_track_index: trackIndex + 1,
        new_track_name: apiGetStr("live_set tracks " + (trackIndex + 1), "name"),
        track_count: apiGetCount("live_set", "tracks")
    };
}

function cmd_create_scene(params) {
    var index = param(params, "index", -1);
    var song = new LiveAPI("live_set");
    var sceneCount = apiGetCount("live_set", "scenes");
    if (index < 0) index = sceneCount;
    song.call("create_scene", index);
    return {
        scene_index: index,
        scene_count: apiGetCount("live_set", "scenes")
    };
}

function cmd_delete_scene(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var sceneName = apiGetStr("live_set scenes " + sceneIndex, "name");
    var song = new LiveAPI("live_set");
    song.call("delete_scene", sceneIndex);
    return {
        deleted_scene: sceneName,
        scene_count: apiGetCount("live_set", "scenes")
    };
}

function cmd_set_scene_name(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var name = param(params, "name", "");
    var scene = new LiveAPI("live_set scenes " + sceneIndex);
    scene.set("name", name);
    return {
        scene_index: sceneIndex,
        name: apiGetStr("live_set scenes " + sceneIndex, "name")
    };
}

function cmd_fire_scene(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var scenePath = "live_set scenes " + sceneIndex;
    var scene = new LiveAPI(scenePath);
    if (!scene.id || scene.id === "0") throw "Scene index out of range";
    scene.call("fire");
    return {
        scene_index: sceneIndex,
        scene_name: apiGetStr(scenePath, "name"),
        fired: true
    };
}

function cmd_create_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var length = param(params, "length", 4.0);
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;

    var hasClip = apiGetNum(slotPath, "has_clip");
    if (hasClip) throw "Clip slot already has a clip";

    var slot = new LiveAPI(slotPath);
    slot.call("create_clip", length);

    var clipPath = slotPath + " clip";
    return {
        name: apiGetStr(clipPath, "name"),
        length: apiGetNum(clipPath, "length")
    };
}

function cmd_create_audio_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var filePath = param(params, "file_path", "");
    var trackPath = "live_set tracks " + trackIndex;

    var hasAudio = apiGetNum(trackPath, "has_audio_input");
    if (!hasAudio) throw "Track " + trackIndex + " is not an audio track";

    var slotPath = trackPath + " clip_slots " + clipIndex;
    var hasClip = apiGetNum(slotPath, "has_clip");
    if (hasClip) throw "Clip slot already has a clip";

    var slot = new LiveAPI(slotPath);
    slot.call("create_clip", filePath);

    var clipPath = slotPath + " clip";
    return {
        name: apiGetStr(clipPath, "name"),
        length: apiGetNum(clipPath, "length"),
        file_path: filePath,
        track_index: trackIndex,
        clip_index: clipIndex
    };
}

function cmd_delete_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var slotPath = trackPath + " clip_slots " + clipIndex;

    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in slot " + clipIndex;

    var trackName = apiGetStr(trackPath, "name");
    var slot = new LiveAPI(slotPath);
    slot.call("delete_clip");

    return {
        track_name: trackName,
        clip_index: clipIndex,
        deleted: true
    };
}

function cmd_duplicate_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var targetIndex = param(params, "target_index", -1);
    var trackPath = getTrackPath(trackIndex);
    var slotPath = trackPath + " clip_slots " + clipIndex;

    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in source slot " + clipIndex;

    var slotCount = apiGetCount(trackPath, "clip_slots");
    if (targetIndex < 0) {
        targetIndex = -1;
        for (var i = 0; i < slotCount; i++) {
            if (!apiGetNum(trackPath + " clip_slots " + i, "has_clip")) {
                targetIndex = i;
                break;
            }
        }
        if (targetIndex < 0) throw "No empty clip slots available";
    }

    if (apiGetNum(trackPath + " clip_slots " + targetIndex, "has_clip")) {
        throw "Target slot " + targetIndex + " already has a clip";
    }

    var slot = new LiveAPI(slotPath);
    var targetSlot = new LiveAPI(trackPath + " clip_slots " + targetIndex);
    slot.call("duplicate_clip_to", targetSlot.id);

    return {
        track_name: apiGetStr(trackPath, "name"),
        source_index: clipIndex,
        target_index: targetIndex,
        duplicated: true
    };
}

function cmd_set_clip_name(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var name = param(params, "name", "");
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;

    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in slot";

    var clipPath = slotPath + " clip";
    var clip = new LiveAPI(clipPath);
    clip.set("name", name);
    return { name: apiGetStr(clipPath, "name") };
}

function cmd_set_clip_loop(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var loopStart = param(params, "loop_start", null);
    var loopEnd = param(params, "loop_end", null);
    var looping = param(params, "looping", null);
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;

    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in slot";

    var clipPath = slotPath + " clip";
    var clip = new LiveAPI(clipPath);

    if (looping !== null) clip.set("looping", looping ? 1 : 0);
    if (loopStart !== null) clip.set("loop_start", Number(loopStart));
    if (loopEnd !== null) clip.set("loop_end", Number(loopEnd));

    return {
        looping: apiGetNum(clipPath, "looping") ? true : false,
        loop_start: apiGetNum(clipPath, "loop_start"),
        loop_end: apiGetNum(clipPath, "loop_end"),
        length: apiGetNum(clipPath, "length")
    };
}

function cmd_fire_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;

    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in slot";

    var slot = new LiveAPI(slotPath);
    slot.call("fire");
    return { fired: true };
}

function cmd_stop_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;
    var slot = new LiveAPI(slotPath);
    slot.call("stop");
    return { stopped: true };
}

function cmd_add_notes_to_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var notes = param(params, "notes", []);
    var arrangementClipIndex = param(params, "arrangement_clip_index", null);
    var clipPath;

    if (arrangementClipIndex !== null) {
        var trackPath = "live_set tracks " + trackIndex;
        var arrangementClipCount = apiGetOptionalCount(trackPath, "arrangement_clips");
        if (arrangementClipIndex < 0 || arrangementClipIndex >= arrangementClipCount) {
            throw "Arrangement clip index out of range (track has " + arrangementClipCount + " arrangement clips)";
        }
        clipPath = trackPath + " arrangement_clips " + arrangementClipIndex;
    } else {
        var slotPath = "live_set tracks " + trackIndex + " clip_slots " + clipIndex;
        if (!apiGetNum(slotPath, "has_clip")) throw "No clip in slot";
        clipPath = slotPath + " clip";
    }

    var clip = new LiveAPI(clipPath);

    if (!apiGetNum(clipPath, "is_midi_clip")) throw "Not a MIDI clip";
    writeNotes(clip, notes);
    return { note_count: notes.length };
}

// ─── Devices, Browser & Automation ───

function cmd_set_device_parameter(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var parameterIndex = param(params, "parameter_index", null);
    var parameterName = param(params, "parameter_name", null);
    var value = param(params, "value", 0.0);
    var trackPath = getTrackPath(trackIndex);
    var devPath = trackPath + " devices " + deviceIndex;
    var paramCount = apiGetCount(devPath, "parameters");
    var list = [];
    var i;
    for (i = 0; i < paramCount; i++) {
        list.push({ index: i, name: apiGetStr(devPath + " parameters " + i, "name") });
    }
    var idx = findParameterIndex(list, parameterIndex, parameterName);
    var pPath = devPath + " parameters " + idx;

    var pApi = new LiveAPI(pPath);
    if (!pApi.id || pApi.id === "0") throw "Parameter index out of range";

    if (value < 0.0 || value > 1.0) throw "Normalized value must be between 0.0 and 1.0";

    var pMin = apiGetNum(pPath, "min");
    var pMax = apiGetNum(pPath, "max");
    var actualValue = pMin + value * (pMax - pMin);
    pApi.set("value", actualValue);

    return {
        parameter_index: idx,
        parameter_name: apiGetStr(pPath, "name"),
        value: apiGetNum(pPath, "value"),
        normalized_value: value,
        display_value: apiGetOptionalStr(pPath, "display_value")
    };
}

function cmd_set_plugin_preset(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var presetIndex = param(params, "preset_index", null);
    var presetName = param(params, "preset_name", null);
    var devPath = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var className = apiGetStr(devPath, "class_name");
    if (className !== "PluginDevice" && className !== "AuPluginDevice") {
        throw "Device is not a VST/AU plug-in";
    }
    var presets = [];
    try {
        var raw = new LiveAPI(devPath).get("presets");
        var i;
        if (raw && raw.length) {
            for (i = 0; i < raw.length; i++) {
                if (raw[i] !== "id") presets.push(String(raw[i]));
            }
        }
    } catch (e) {}
    if (presetName) {
        var needle = String(presetName).toLowerCase();
        var matches = [];
        var j;
        for (j = 0; j < presets.length; j++) {
            if (presets[j].toLowerCase() === needle) matches.push(j);
        }
        if (matches.length !== 1) throw "preset_name not found or ambiguous (host bank may be empty for VST3)";
        presetIndex = matches[0];
    }
    if (presetIndex === null || presetIndex === undefined) throw "preset_index or preset_name is required";
    var dev = new LiveAPI(devPath);
    dev.set("selected_preset_index", presetIndex);
    var selected = apiGetNum(devPath, "selected_preset_index");
    return {
        device_name: apiGetStr(devPath, "name"),
        selected_preset_index: selected,
        preset_name: (selected >= 0 && selected < presets.length) ? presets[selected] : null,
        preset_count: presets.length,
        note: "This is the plug-in host program bank, not Serum .serumpreset files."
    };
}

function cmd_batch_set_device_parameters(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var parameterIndices = param(params, "parameter_indices", null);
    var parameterNames = param(params, "parameter_names", null);
    var values = param(params, "values", []);
    var trackPath = getTrackPath(trackIndex);
    var devPath = trackPath + " devices " + deviceIndex;
    var paramCount = apiGetCount(devPath, "parameters");
    var list = [];
    var i;
    for (i = 0; i < paramCount; i++) {
        list.push({ index: i, name: apiGetStr(devPath + " parameters " + i, "name") });
    }
    var useNames = parameterNames && parameterNames.length;
    var keys = useNames ? parameterNames : (parameterIndices || []);
    if (keys.length !== values.length) throw "names/indices and values must have the same length";

    var updated = [];
    var skipped = [];
    for (i = 0; i < keys.length; i++) {
        var val = values[i];
        if (val < 0.0 || val > 1.0) {
            skipped.push({ name: keys[i], reason: "value_out_of_range" });
            continue;
        }
        var pIdx;
        try {
            pIdx = useNames ? findParameterIndex(list, null, keys[i]) : findParameterIndex(list, keys[i], null);
        } catch (lookupErr) {
            skipped.push({ name: keys[i], reason: "not_configured" });
            continue;
        }
        var pPath = devPath + " parameters " + pIdx;
        var pMin = apiGetNum(pPath, "min");
        var pMax = apiGetNum(pPath, "max");
        var actualVal = pMin + val * (pMax - pMin);
        var p = new LiveAPI(pPath);
        p.set("value", actualVal);
        updated.push({
            index: pIdx,
            name: apiGetStr(pPath, "name"),
            value: apiGetNum(pPath, "value"),
            normalized_value: val
        });
    }

    return {
        updated_count: updated.length,
        skipped_count: skipped.length,
        parameters: updated,
        skipped: skipped
    };
}

function cmd_delete_device(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var devPath = trackPath + " devices " + deviceIndex;

    var devName = apiGetStr(devPath, "name");
    var track = new LiveAPI(trackPath);
    track.call("delete_device", deviceIndex);

    return {
        deleted_device: devName,
        device_count: apiGetCount(trackPath, "devices")
    };
}

function cmd_load_instrument_or_effect(params) {
    throw "Browser/instrument loading is not accessible from Max for Live devices. Drag instruments manually from Ableton's browser, or use the Remote Script backend instead.";
}

function cmd_set_clip_envelope(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var parameterIndex = param(params, "parameter_index", 0);
    var points = param(params, "points", []);
    var trackPath = getTrackPath(trackIndex);
    var clipPath = sessionClipPath(params);
    var pPath = trackPath + " devices " + deviceIndex + " parameters " + parameterIndex;
    var pMin = apiGetNum(pPath, "min");
    var pMax = apiGetNum(pPath, "max");
    var paramName = apiGetStr(pPath, "name");

    var clip = new LiveAPI(clipPath);
    var paramApi = new LiveAPI(pPath);

    if (clipIsArrangement(params, clipPath)) {
        throw "Arrangement clip envelopes are not in the LOM (session only)";
    }

    // Try to get or create envelope
    var envId = clip.call("automation_envelope", "id", paramApi.id);
    if (!envId || envId === "0" || envId === 0) {
        envId = clip.call("create_automation_envelope", "id", paramApi.id);
    }
    if (!envId || envId === "0" || envId === 0) {
        throw "Could not create automation envelope for parameter";
    }

    var env = new LiveAPI("id " + envId);

    // Sort points by time and interpolate
    var sorted = [];
    for (var i = 0; i < points.length; i++) {
        sorted.push({
            time: Number(points[i].time || 0),
            value: Number(points[i].value || 0)
        });
    }
    sorted.sort(function (a, b) { return a.time - b.time; });

    var stepSize = 0.25;
    for (var s = 0; s < sorted.length - 1; s++) {
        var t0 = sorted[s].time;
        var v0 = sorted[s].value;
        var t1 = sorted[s + 1].time;
        var v1 = sorted[s + 1].value;
        var segDur = t1 - t0;
        var numSteps = Math.max(1, Math.floor(segDur / stepSize));
        for (var st = 0; st < numSteps; st++) {
            var frac = st / numSteps;
            var t = t0 + frac * segDur;
            var v = v0 + frac * (v1 - v0);
            var actual = pMin + v * (pMax - pMin);
            env.call("insert_step", t, stepSize, actual);
        }
    }
    // Last point holds for 1 beat
    if (sorted.length > 0) {
        var last = sorted[sorted.length - 1];
        var lastActual = pMin + last.value * (pMax - pMin);
        env.call("insert_step", last.time, 1.0, lastActual);
    }

    return {
        track_index: trackIndex,
        clip_index: clipIndex,
        device_index: deviceIndex,
        parameter_index: parameterIndex,
        parameter_name: paramName,
        points_set: points.length
    };
}

function cmd_clear_clip_envelope(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = param(params, "clip_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var parameterIndex = param(params, "parameter_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var clipPath = sessionClipPath(params);
    var pPath = trackPath + " devices " + deviceIndex + " parameters " + parameterIndex;
    var paramName = apiGetStr(pPath, "name");

    var clip = new LiveAPI(clipPath);
    var paramApi = new LiveAPI(pPath);
    clip.call("clear_envelope", "id", paramApi.id);

    return {
        track_index: trackIndex,
        clip_index: clipIndex,
        parameter_name: paramName,
        cleared: true
    };
}

// ─── Ported from the Python Remote Script (routing, arrangement clips, record_arrangement) ───

// LiveAPI returns dictionary-valued properties (routing types, get_notes_extended) as a JSON
// string, usually wrapped as {"<prop>": ...}. Normalise to a plain JS value.
function apiGetJson(api, prop) {
    var raw = api.get(prop);
    if (raw instanceof Array) raw = raw.join(" ");
    raw = String(raw);
    var parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (e) {
        throw "Could not parse " + prop + " as JSON: " + raw;
    }
    if (parsed && typeof parsed === "object" && parsed.hasOwnProperty(prop)) return parsed[prop];
    return parsed;
}

function parseCallJson(raw) {
    if (raw instanceof Array) raw = raw.join(" ");
    return JSON.parse(String(raw));
}

function routingName(r) {
    if (!r) return "";
    return r.display_name !== undefined ? String(r.display_name) : String(r);
}

function cmd_get_track_routing(params) {
    var trackIndex = param(params, "track_index", 0);
    var track = getTrack(trackIndex);
    if (!track.id || track.id === "0") throw "Track index out of range: " + trackIndex;

    var result = {
        input_routing_type: routingName(apiGetJson(track, "input_routing_type")),
        output_routing_type: routingName(apiGetJson(track, "output_routing_type"))
    };
    var avIn = apiGetJson(track, "available_input_routing_types") || [];
    var avOut = apiGetJson(track, "available_output_routing_types") || [];
    result.available_input_routing_types = [];
    result.available_output_routing_types = [];
    var i;
    for (i = 0; i < avIn.length; i++) result.available_input_routing_types.push({ display_name: routingName(avIn[i]) });
    for (i = 0; i < avOut.length; i++) result.available_output_routing_types.push({ display_name: routingName(avOut[i]) });
    return result;
}

function setRouting(trackIndex, prop, availableProp, wantedName, caseInsensitive) {
    var track = getTrack(trackIndex);
    if (!track.id || track.id === "0") throw "Track index out of range: " + trackIndex;

    var available = apiGetJson(track, availableProp) || [];
    var names = [];
    for (var i = 0; i < available.length; i++) {
        var name = routingName(available[i]);
        names.push(name);
        var match = caseInsensitive ? (name.toLowerCase() === String(wantedName).toLowerCase()) : (name === wantedName);
        if (match) {
            // Setting a routing takes the dictionary back (identifier is what Live keys on).
            track.set(prop, JSON.stringify({ display_name: name, identifier: available[i].identifier }));
            var now = routingName(apiGetJson(track, prop));
            if (now !== name) throw "Live did not accept routing " + name + " (still " + now + ")";
            return name;
        }
    }
    throw "Routing type not found: " + wantedName + ". Available: " + names.join(", ");
}

function setRoutingOnApi(api, prop, availableProp, wantedName, caseInsensitive) {
    var available = apiGetJson(api, availableProp) || [];
    var names = [];
    for (var i = 0; i < available.length; i++) {
        var name = routingName(available[i]);
        names.push(name);
        var match = caseInsensitive ? (name.toLowerCase() === String(wantedName).toLowerCase()) : (name === wantedName);
        if (match) {
            api.set(prop, JSON.stringify({ display_name: name, identifier: available[i].identifier }));
            var now = routingName(apiGetJson(api, prop));
            if (now !== name) throw "Live did not accept routing " + name + " (still " + now + ")";
            return name;
        }
    }
    throw "Routing type not found: " + wantedName + ". Available: " + names.join(", ");
}

function cmd_set_track_input_routing(params) {
    var name = setRouting(param(params, "track_index", 0), "input_routing_type",
        "available_input_routing_types", param(params, "routing_type_name", ""), false);
    return { input_routing_type: name };
}

function cmd_set_track_output_routing(params) {
    var name = setRouting(param(params, "track_index", 0), "output_routing_type",
        "available_output_routing_types", param(params, "routing_type_name", ""), true);
    return { output_routing_type: name };
}

function cmd_set_track_monitoring(params) {
    var trackIndex = param(params, "track_index", 0);
    var state = Math.floor(param(params, "state", 1)); // 0=In, 1=Auto, 2=Off
    var track = getTrack(trackIndex);
    if (!track.id || track.id === "0") throw "Track index out of range: " + trackIndex;
    track.set("current_monitoring_state", state);
    return { monitoring_state: apiGetNum(getTrackPath(trackIndex), "current_monitoring_state") };
}

// Read every note in a clip via get_notes_extended (Live 11+), falling back to the
// select-all protocol used by cmd_get_clip_notes.
function readAllNotes(clip, clipLength) {
    try {
        var data = parseCallJson(clip.call("get_notes_extended", 0, 128, 0, clipLength));
        var notes = data.notes || [];
        var out = [];
        for (var i = 0; i < notes.length; i++) {
            out.push(copyNoteDictionary(notes[i]));
        }
        return out;
    } catch (e) {
        post("get_notes_extended failed (" + e + "), falling back to get_selected_notes\n");
    }
    clip.call("select_all_notes");
    var rawNotes = clip.call("get_selected_notes");
    var list = [];
    if (rawNotes && rawNotes.length > 2) {
        var count = Number(rawNotes[1]);
        var idx = 2;
        for (var n = 0; n < count; n++) {
            if (idx + 5 > rawNotes.length) break;
            list.push({
                pitch: Number(rawNotes[idx + 1]),
                start_time: Number(rawNotes[idx + 2]),
                duration: Number(rawNotes[idx + 3]),
                velocity: Number(rawNotes[idx + 4]),
                mute: Number(rawNotes[idx + 5]) ? true : false
            });
            idx += 6;
        }
    }
    clip.call("deselect_all_notes");
    return list;
}

function copyNoteDictionary(note) {
    var copy = {};
    var key;
    for (key in note) {
        if (note.hasOwnProperty(key)) copy[key] = note[key];
    }
    if (copy.note_id !== undefined && copy.note_id !== null) copy.note_id = Number(copy.note_id);
    if (copy.pitch !== undefined) copy.pitch = Number(copy.pitch);
    if (copy.start_time !== undefined) copy.start_time = Number(copy.start_time);
    if (copy.duration !== undefined) copy.duration = Number(copy.duration);
    if (copy.velocity !== undefined) copy.velocity = Number(copy.velocity);
    if (copy.mute !== undefined) copy.mute = copy.mute ? true : false;
    return copy;
}

// Live 11+ add_new_notes. Do not call set_notes / replace_selected_notes (Live 11 modal).
function writeNotes(clip, notes) {
    var specs = [];
    var i;
    for (i = 0; i < notes.length; i++) {
        var n = notes[i];
        specs.push({
            pitch: n.pitch !== undefined ? Math.floor(n.pitch) : 60,
            start_time: n.start_time !== undefined ? Number(n.start_time) : 0.0,
            duration: n.duration !== undefined ? Number(n.duration) : 0.25,
            velocity: n.velocity !== undefined ? Math.floor(n.velocity) : 100,
            mute: n.mute ? 1 : 0
        });
    }
    clip.call("add_new_notes", { notes: specs });
    return notes.length;
}

function getArrangementClip(trackIndex, arrangementClipIndex) {
    var trackPath = "live_set tracks " + trackIndex;
    var count = apiGetCount(trackPath, "arrangement_clips");
    if (arrangementClipIndex < 0 || arrangementClipIndex >= count) {
        throw "Arrangement clip index out of range (track has " + count + " arrangement clips)";
    }
    return new LiveAPI(trackPath + " arrangement_clips " + arrangementClipIndex);
}

function cmd_get_arrangement_clip_notes(params) {
    var trackIndex = param(params, "track_index", 0);
    var idx = param(params, "arrangement_clip_index", 0);
    var clip = getArrangementClip(trackIndex, idx);
    if (!apiGetNum(clip.unquotedpath, "is_midi_clip")) throw "Not a MIDI clip";

    var clipLength = apiGetNum(clip.unquotedpath, "length");
    var notes = readAllNotes(clip, clipLength);
    return {
        track_index: trackIndex,
        arrangement_clip_index: idx,
        clip_name: apiGetStr(clip.unquotedpath, "name"),
        start_time: apiGetNum(clip.unquotedpath, "start_time"),
        length: clipLength,
        note_count: notes.length,
        notes: notes
    };
}

function cmd_delete_arrangement_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var idx = param(params, "arrangement_clip_index", 0);
    var trackPath = "live_set tracks " + trackIndex;
    var clip = getArrangementClip(trackIndex, idx);
    var before = apiGetCount(trackPath, "arrangement_clips");

    var track = new LiveAPI(trackPath);
    track.call("delete_clip", "id " + clip.id);

    var after = apiGetCount(trackPath, "arrangement_clips");
    if (after !== before - 1) throw "delete_clip did not remove the clip (count " + before + " -> " + after + ")";
    return { track_index: trackIndex, deleted_index: idx, remaining_count: after };
}

function findArrangementClipIndex(trackPath, startTime) {
    var count = apiGetCount(trackPath, "arrangement_clips");
    for (var i = 0; i < count; i++) {
        if (Math.abs(apiGetNum(trackPath + " arrangement_clips " + i, "start_time") - startTime) < 0.001) return i;
    }
    return -1;
}

function cmd_create_arrangement_midi_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var start = Number(param(params, "time", 0.0));
    var length = Number(param(params, "length", 4.0));
    var notes = param(params, "notes", null);
    var trackPath = "live_set tracks " + trackIndex;

    if (trackIndex < 0 || trackIndex >= apiGetCount("live_set", "tracks")) throw "Track index out of range";
    if (!apiGetNum(trackPath, "has_midi_input")) throw "Track " + trackIndex + " is not a MIDI track";

    var track = new LiveAPI(trackPath);
    // Live 11+: Track.create_midi_clip(start_time, length) in beats
    track.call("create_midi_clip", start.toFixed(8), length.toFixed(8));

    var idx = findArrangementClipIndex(trackPath, start);
    if (idx < 0) throw "create_midi_clip did not produce a clip at " + start;
    var clip = new LiveAPI(trackPath + " arrangement_clips " + idx);

    var noteCount = 0;
    if (notes && notes.length) noteCount = writeNotes(clip, notes);

    return {
        track_index: trackIndex,
        start_time: start,
        length: apiGetNum(clip.unquotedpath, "length"),
        note_count: noteCount,
        arrangement_clip_index: idx,
        name: apiGetStr(clip.unquotedpath, "name")
    };
}

function cmd_create_arrangement_audio_clip(params) {
    var trackIndex = param(params, "track_index", 0);
    var filePath = param(params, "file_path", "");
    var start = Number(param(params, "time", 0.0));
    var length = param(params, "length", null);
    var trackPath = "live_set tracks " + trackIndex;

    if (trackIndex < 0 || trackIndex >= apiGetCount("live_set", "tracks")) throw "Track index out of range";
    if (!apiGetNum(trackPath, "has_audio_input")) throw "Track " + trackIndex + " is not an audio track";

    var track = new LiveAPI(trackPath);
    // Live 11+: Track.create_audio_clip(file_path, position)
    track.call("create_audio_clip", filePath, start.toFixed(8));

    var idx = findArrangementClipIndex(trackPath, start);
    if (idx < 0) throw "create_audio_clip did not produce a clip at " + start + " (bad file path?)";
    var clip = new LiveAPI(trackPath + " arrangement_clips " + idx);

    // `length` is accepted for parity with the Remote Script but neither backend can trim an
    // arrangement audio clip: end_time is read-only and end_marker does not change the
    // arrangement span. The clip takes the sample's full length; end_time below is the truth.

    return {
        track_index: trackIndex,
        file_path: filePath,
        start_time: start,
        end_time: apiGetNum(clip.unquotedpath, "end_time"),
        length: apiGetNum(clip.unquotedpath, "length"),
        name: apiGetStr(clip.unquotedpath, "name"),
        arrangement_clip_index: idx
    };
}

// record_arrangement: fire scenes in sequence while Live records session -> arrangement.
// Same strategy as the Remote Script: 1-bar clip trigger quantization, fire the next scene
// two beats before the section boundary, poll current_song_time with a Task.
function cmd_record_arrangement(params) {
    var sections = param(params, "sections", []);
    var startTime = Number(param(params, "start_time", 0.0));
    if (!sections.length) throw "No sections given";

    return deferred(function (resolve, reject) {
        var song = new LiveAPI("live_set");
        var tempo = apiGetNum("live_set", "tempo");
        var beatsPerBar = apiGetNum("live_set", "signature_numerator");
        var sceneCount = apiGetCount("live_set", "scenes");
        var savedQuant = apiGetNum("live_set", "clip_trigger_quantization");

        var state = {
            i: -1, totalBars: 0, recorded: [], targetBeat: 0, fireBeat: null, nextFired: false, pollTask: null
        };

        function fireScene(idx) {
            var scene = new LiveAPI("live_set scenes " + idx);
            scene.call("fire");
            return apiGetStr("live_set scenes " + idx, "name");
        }

        function cleanup(ok) {
            try { if (state.pollTask) state.pollTask.cancel(); } catch (e) {}
            try { song.set("record_mode", 0); } catch (e) {}
            try { song.call("stop_playing"); } catch (e) {}
            try { song.set("clip_trigger_quantization", savedQuant); } catch (e) {}
            if (ok) {
                try { song.call("stop_all_clips"); } catch (e) {}
                try { song.set("back_to_arranger", 1); } catch (e) {}
                try { song.set("current_song_time", 0); } catch (e) {}
            }
        }

        function nextSection() {
            state.i++;
            while (state.i < sections.length) {
                var si = Math.floor(sections[state.i].scene_index || 0);
                if (si >= 0 && si < sceneCount) break;
                post("record_arrangement: skipping invalid scene index " + si + "\n");
                state.i++;
            }
            if (state.i >= sections.length) {
                cleanup(true);
                resolve({
                    total_bars: state.totalBars,
                    total_beats: state.totalBars * beatsPerBar,
                    sections: state.recorded,
                    tempo: tempo
                });
                return;
            }

            var sec = sections[state.i];
            var sceneIdx = Math.floor(sec.scene_index || 0);
            var bars = Math.floor(sec.bars || 8);
            var sceneName = (state.i === 0 || !state.nextFired)
                ? fireScene(sceneIdx)
                : apiGetStr("live_set scenes " + sceneIdx, "name");

            state.targetBeat = startTime + (state.totalBars + bars) * beatsPerBar;
            state.nextFired = false;
            state.fireBeat = null;
            // Look ahead for the next valid section so we can pre-fire it
            for (var j = state.i + 1; j < sections.length; j++) {
                var nsi = Math.floor(sections[j].scene_index || 0);
                if (nsi >= 0 && nsi < sceneCount) { state.fireBeat = state.targetBeat - 2.0; state.nextSceneIdx = nsi; break; }
            }

            state.recorded.push({
                scene_index: sceneIdx, scene_name: sceneName, bars: bars,
                start_bar: state.totalBars + 1, end_bar: state.totalBars + bars
            });
            state.totalBars += bars;
            post("record_arrangement: section " + (state.i + 1) + " scene " + sceneIdx + " (" + sceneName + ") for " + bars + " bars\n");
        }

        function poll() {
            try {
                var current = apiGetNum("live_set", "current_song_time");
                if (state.fireBeat !== null && !state.nextFired && current >= state.fireBeat) {
                    fireScene(state.nextSceneIdx);
                    state.nextFired = true;
                }
                if (current >= state.targetBeat - 0.5) {
                    nextSection();
                    if (state.i >= sections.length) return; // resolved in nextSection
                }
                state.pollTask = new Task(poll);
                state.pollTask.schedule(20);
            } catch (e) {
                cleanup(false);
                reject(e);
            }
        }

        try {
            song.set("clip_trigger_quantization", 4); // 1 Bar
            var trackCount = apiGetCount("live_set", "tracks");
            for (var t = 0; t < trackCount; t++) {
                var tp = "live_set tracks " + t;
                if (apiGetNum(tp, "can_be_armed") && apiGetNum(tp, "arm")) new LiveAPI(tp).set("arm", 0);
            }
            if (apiGetNum("live_set", "is_playing")) song.call("stop_playing");
            song.set("back_to_arranger", 1);
            song.set("current_song_time", startTime);
            song.set("record_mode", 1);
            nextSection();
            state.pollTask = new Task(poll);
            state.pollTask.schedule(20);
        } catch (e) {
            cleanup(false);
            reject(e);
        }
    });
}

function setNormalizedMixerParam(paramPath, normalized, label) {
    if (normalized < 0.0 || normalized > 1.0) throw label + " must be between 0.0 and 1.0";
    var pMin = apiGetNum(paramPath, "min");
    var pMax = apiGetNum(paramPath, "max");
    var pApi = new LiveAPI(paramPath);
    pApi.set("value", pMin + normalized * (pMax - pMin));
    return apiGetNum(paramPath, "value");
}

function cmd_get_groove_pool() {
    var count = apiGetOptionalCount("live_set groove_pool", "grooves");
    var grooves = [];
    for (var i = 0; i < count; i++) {
        var gPath = "live_set groove_pool grooves " + i;
        grooves.push({
            index: i,
            name: apiGetOptionalStr(gPath, "name"),
            amount: apiGetOptionalNum(gPath, "amount")
        });
    }
    return {
        groove_amount: apiGetOptionalNum("live_set", "groove_amount"),
        grooves: grooves
    };
}

function cmd_set_groove_amount(params) {
    var amount = Number(param(params, "amount", 0));
    if (amount < 0.0 || amount > 1.0) throw "Groove amount must be between 0.0 and 1.0";
    var song = new LiveAPI("live_set");
    song.set("groove_amount", amount);
    return { groove_amount: apiGetNum("live_set", "groove_amount") };
}

function cmd_apply_groove(params) {
    var clipPath = sessionClipPath(params);
    var grooveIndex = param(params, "groove_index", 0);
    var groovePath = "live_set groove_pool grooves " + grooveIndex;
    var grooveApi = new LiveAPI(groovePath);
    if (!grooveApi.id || grooveApi.id === "0") throw "Groove index out of range";
    var clip = new LiveAPI(clipPath);
    clip.set("groove", "id", grooveApi.id);
    return {
        applied: true,
        groove_index: grooveIndex,
        groove_name: apiGetOptionalStr(groovePath, "name")
    };
}

function cmd_clear_clip_groove(params) {
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    clip.set("groove", "id", 0);
    return { cleared: true };
}

function cmd_get_device_sidechain(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var device = new LiveAPI(getTrackPath(trackIndex) + " devices " + deviceIndex);
    if (!device.id || device.id === "0") throw "Device index out of range";
    var typeVal;
    var chanVal;
    try {
        typeVal = apiGetJson(device, "input_routing_type");
        chanVal = apiGetJson(device, "input_routing_channel");
    } catch (e) {
        return { supported: false };
    }
    var result = {
        supported: true,
        input_routing_type: routingName(typeVal),
        input_routing_channel: routingName(chanVal),
        available_input_routing_types: [],
        available_input_routing_channels: []
    };
    try {
        var avIn = apiGetJson(device, "available_input_routing_types") || [];
        var avCh = apiGetJson(device, "available_input_routing_channels") || [];
        var i;
        for (i = 0; i < avIn.length; i++) result.available_input_routing_types.push({ display_name: routingName(avIn[i]) });
        for (i = 0; i < avCh.length; i++) result.available_input_routing_channels.push({ display_name: routingName(avCh[i]) });
    } catch (availErr) {
        // Device supports sidechain routing but did not expose the available-lists dict.
    }
    return result;
}

function cmd_set_device_sidechain(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var typeName = param(params, "routing_type_name", null);
    if (typeName === null) typeName = param(params, "input_routing_type", null);
    var channelName = param(params, "channel_name", null);
    if (channelName === null) channelName = param(params, "input_routing_channel", null);
    var device = new LiveAPI(getTrackPath(trackIndex) + " devices " + deviceIndex);
    if (!device.id || device.id === "0") throw "Device index out of range";
    try {
        apiGetJson(device, "input_routing_type");
    } catch (e) {
        return { supported: false };
    }
    var result = { supported: true };
    if (typeName) {
        result.input_routing_type = setRoutingOnApi(device, "input_routing_type",
            "available_input_routing_types", typeName, false);
    } else {
        result.input_routing_type = routingName(apiGetJson(device, "input_routing_type"));
    }
    if (channelName) {
        result.input_routing_channel = setRoutingOnApi(device, "input_routing_channel",
            "available_input_routing_channels", channelName, false);
    } else {
        try {
            result.input_routing_channel = routingName(apiGetJson(device, "input_routing_channel"));
        } catch (chanErr) {
            result.input_routing_channel = "";
        }
    }
    return result;
}

function cmd_get_rack_chains(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var devPath = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var dev = new LiveAPI(devPath);
    if (!dev.id || dev.id === "0") throw "Device index out of range";
    if (!apiGetOptionalNum(devPath, "can_have_chains")) throw "Device cannot have chains";
    var count = apiGetOptionalCount(devPath, "chains");
    var chains = [];
    for (var i = 0; i < count; i++) {
        var cPath = devPath + " chains " + i;
        chains.push({
            index: i,
            name: apiGetOptionalStr(cPath, "name"),
            mute: apiGetOptionalNum(cPath, "mute") ? true : false,
            solo: apiGetOptionalNum(cPath, "solo") ? true : false,
            volume: apiGetOptionalNum(cPath + " mixer_device volume", "value"),
            device_count: apiGetOptionalCount(cPath, "devices")
        });
    }
    return {
        track_index: trackIndex,
        device_index: deviceIndex,
        chain_count: chains.length,
        chains: chains
    };
}

function cmd_insert_rack_chain(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var index = param(params, "index", -1);
    var name = param(params, "name", null);
    var devPath = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var device = new LiveAPI(devPath);
    if (!device.id || device.id === "0") throw "Device index out of range";
    if (!apiGetOptionalNum(devPath, "can_have_chains")) throw "Device cannot have chains";
    var chainIndex = index;
    try {
        if (index < 0) {
            device.call("insert_chain");
            chainIndex = apiGetOptionalCount(devPath, "chains") - 1;
        } else {
            device.call("insert_chain", index);
            chainIndex = index;
        }
    } catch (e) {
        throw "insert_chain failed (requires Live 12.3+): " + e;
    }
    if (name && chainIndex >= 0) {
        var chain = new LiveAPI(devPath + " chains " + chainIndex);
        chain.set("name", name);
    }
    return {
        inserted: true,
        chain_index: chainIndex,
        name: chainIndex >= 0 ? apiGetOptionalStr(devPath + " chains " + chainIndex, "name") : name,
        chain_count: apiGetOptionalCount(devPath, "chains")
    };
}

function cmd_set_chain_mixer(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var chainIndex = param(params, "chain_index", 0);
    var mute = param(params, "mute", null);
    var solo = param(params, "solo", null);
    var volume = param(params, "volume", null);
    var panning = param(params, "panning", null);
    var chainPath = getTrackPath(trackIndex) + " devices " + deviceIndex + " chains " + chainIndex;
    var chain = new LiveAPI(chainPath);
    if (!chain.id || chain.id === "0") throw "Chain index out of range";
    if (mute !== null) chain.set("mute", mute ? 1 : 0);
    if (solo !== null) chain.set("solo", solo ? 1 : 0);
    if (volume !== null) setNormalizedMixerParam(chainPath + " mixer_device volume", Number(volume), "Volume");
    if (panning !== null) setNormalizedMixerParam(chainPath + " mixer_device panning", canonicalPanning(panning), "Panning");
    var result = {
        track_index: trackIndex,
        device_index: deviceIndex,
        chain_index: chainIndex,
        name: apiGetOptionalStr(chainPath, "name"),
        mute: apiGetOptionalNum(chainPath, "mute") ? true : false,
        solo: apiGetOptionalNum(chainPath, "solo") ? true : false
    };
    var volVal = apiGetOptionalNum(chainPath + " mixer_device volume", "value");
    if (volVal !== null) result.volume = volVal;
    var panVal = apiGetOptionalNum(chainPath + " mixer_device panning", "value");
    if (panVal !== null) result.panning = panVal;
    return result;
}

function cmd_get_rack_macros(params) {
    return rackMacroState(rackDevice(params));
}

function cmd_move_device(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var targetIndex = param(params, "target_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    if (!track.id || track.id === "0") throw "Track index out of range";
    var device = new LiveAPI(trackPath + " devices " + deviceIndex);
    if (!device.id || device.id === "0") throw "Device index out of range";
    try {
        track.call("move_device", deviceIndex, targetIndex);
    } catch (e) {
        try {
            var song = new LiveAPI("live_set");
            song.call("move_device", "id", device.id, "id", track.id, targetIndex);
        } catch (e2) {
            throw "Live cannot place an instrument before MIDI effects; load already inserts MIDI FX before the instrument; use move_device to reorder MIDI FX";
        }
    }
    return { moved: true, target_index: targetIndex };
}

function cmd_capture_and_insert_scene() {
    var song = new LiveAPI("live_set");
    song.call("capture_and_insert_scene");
    return {
        captured: true,
        scene_count: apiGetCount("live_set", "scenes")
    };
}

function cmd_crop_clip(params) {
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    clip.call("crop");
    var length = apiGetNum(clipPath, "length");
    clip.set("loop_end", length);
    clip.set("loop_start", 0);
    clip.set("end_marker", length);
    clip.set("start_marker", 0);
    return {
        cropped: true,
        length: apiGetNum(clipPath, "length"),
        loop_start: apiGetOptionalNum(clipPath, "loop_start"),
        loop_end: apiGetOptionalNum(clipPath, "loop_end"),
        start_marker: apiGetOptionalNum(clipPath, "start_marker"),
        end_marker: apiGetOptionalNum(clipPath, "end_marker")
    };
}

function cmd_set_clip_launch(params) {
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    var launchMode = param(params, "launch_mode", null);
    var launchQuant = param(params, "launch_quantization", null);
    var legato = param(params, "legato", null);
    if (launchMode !== null) clip.set("launch_mode", Math.floor(launchMode));
    if (launchQuant !== null) clip.set("launch_quantization", Math.floor(launchQuant));
    if (legato !== null) clip.set("legato", legato ? 1 : 0);
    var result = {};
    var mode = apiGetOptionalNum(clipPath, "launch_mode");
    var quant = apiGetOptionalNum(clipPath, "launch_quantization");
    var leg = apiGetOptionalNum(clipPath, "legato");
    if (mode !== null) result.launch_mode = mode;
    if (quant !== null) result.launch_quantization = quant;
    if (leg !== null) result.legato = leg ? true : false;
    return result;
}

function cmd_get_cue_points() {
    var count = apiGetOptionalCount("live_set", "cue_points");
    var points = [];
    for (var i = 0; i < count; i++) {
        var p = "live_set cue_points " + i;
        points.push({
            index: i,
            name: apiGetOptionalStr(p, "name"),
            time: apiGetOptionalNum(p, "time")
        });
    }
    return { cue_points: points };
}

function cmd_toggle_cue() {
    var song = new LiveAPI("live_set");
    song.call("set_or_delete_cue");
    return {
        toggled: true,
        cue_count: apiGetOptionalCount("live_set", "cue_points")
    };
}

function cmd_jump_to_cue(params) {
    var direction = param(params, "direction", null);
    var index = param(params, "index", null);
    if (direction === "next" || direction === "prev") {
        var now = apiGetNum("live_set", "current_song_time");
        var count = apiGetOptionalCount("live_set", "cue_points");
        if (!count) throw "No cue points";
        var cues = [];
        var i;
        for (i = 0; i < count; i++) {
            var p = "live_set cue_points " + i;
            cues.push({
                index: i,
                name: apiGetOptionalStr(p, "name"),
                time: apiGetOptionalNum(p, "time")
            });
        }
        var chosen = null;
        for (i = 0; i < cues.length; i++) {
            var t = cues[i].time;
            if (t === null || t === undefined) continue;
            if (direction === "next") {
                if (t > now && (chosen === null || t < chosen.time)) chosen = cues[i];
            } else if (t < now && (chosen === null || t > chosen.time)) {
                chosen = cues[i];
            }
        }
        if (chosen === null) {
            for (i = 0; i < cues.length; i++) {
                var wt = cues[i].time;
                if (wt === null || wt === undefined) continue;
                if (direction === "next") {
                    if (chosen === null || wt < chosen.time) chosen = cues[i];
                } else if (chosen === null || wt > chosen.time) {
                    chosen = cues[i];
                }
            }
        }
        if (chosen === null) throw "No cue points";
        var jumped = jumpToCueIndex(chosen.index);
        jumped.direction = direction;
        return jumped;
    }
    if (index !== null && index !== undefined) {
        return jumpToCueIndex(index);
    }
    throw "jump_to_cue requires direction (next/prev) or index";
}

function cmd_set_crossfader(params) {
    var value = Number(param(params, "value", 0.5));
    var actual = setNormalizedMixerParam("live_set master_track mixer_device crossfader", value, "Crossfader value");
    return {
        value: actual,
        normalized_value: value
    };
}

function cmd_set_crossfade_assign(params) {
    var trackIndex = param(params, "track_index", 0);
    var assign = Math.floor(param(params, "assign", 1));
    var mixerPath = getTrackPath(trackIndex) + " mixer_device";
    var mixer = new LiveAPI(mixerPath);
    if (!mixer.id || mixer.id === "0") throw "Track index out of range";
    mixer.set("crossfade_assign", assign);
    return {
        track_index: trackIndex,
        crossfade_assign: apiGetNum(mixerPath, "crossfade_assign")
    };
}

function cmd_show_view(params) {
    var viewName = param(params, "view_name", "Session");
    var view = new LiveAPI("live_app view");
    view.call("show_view", viewName);
    return { shown: true, view_name: viewName };
}

function cmd_get_warp_markers(params) {
    var clipPath = sessionClipPath(params);
    if (!apiGetOptionalNum(clipPath, "is_audio_clip")) throw "Not an audio clip";
    var count = apiGetOptionalCount(clipPath, "warp_markers");
    var markers = [];
    for (var i = 0; i < count; i++) {
        var mPath = clipPath + " warp_markers " + i;
        markers.push({
            index: i,
            beat_time: apiGetOptionalNum(mPath, "beat_time"),
            sample_time: apiGetOptionalNum(mPath, "sample_time")
        });
    }
    return { warp_markers: markers };
}

function cmd_add_warp_marker(params) {
    var clipPath = sessionClipPath(params);
    if (!apiGetOptionalNum(clipPath, "is_audio_clip")) throw "Not an audio clip";
    var beatTime = Number(param(params, "beat_time", 0));
    var sampleTime = param(params, "sample_time", null);
    var clip = new LiveAPI(clipPath);
    if (apiGetOptionalNum(clipPath, "warping") !== null) {
        clip.set("warping", 1);
    }
    var marker = { beat_time: beatTime };
    if (sampleTime !== null && sampleTime !== undefined) marker.sample_time = Number(sampleTime);
    var added = false;
    var err = null;
    try {
        clip.call("add_warp_marker", marker);
        added = true;
    } catch (e1) {
        err = e1;
        try {
            clip.call("add_warp_marker", beatTime);
            added = true;
        } catch (e2) {
            err = e2;
        }
    }
    if (!added) throw "add_warp_marker failed: " + err;
    var result = { added: true, beat_time: beatTime };
    if (sampleTime !== null && sampleTime !== undefined) result.sample_time = Number(sampleTime);
    return result;
}

function cmd_move_warp_marker(params) {
    var clipPath = sessionClipPath(params);
    if (!apiGetOptionalNum(clipPath, "is_audio_clip")) throw "Not an audio clip";
    var beatTime = Number(param(params, "beat_time", 0));
    var distance = Number(param(params, "beat_time_distance", 0));
    var clip = new LiveAPI(clipPath);
    try {
        clip.call("move_warp_marker", beatTime, distance);
    } catch (e) {
        throw "move_warp_marker is not available on this clip";
    }
    return { moved: true, beat_time: beatTime, beat_time_distance: distance };
}

function cmd_delete_warp_marker(params) {
    var clipPath = sessionClipPath(params);
    if (!apiGetOptionalNum(clipPath, "is_audio_clip")) throw "Not an audio clip";
    var beatTime = Number(param(params, "beat_time", 0));
    var clip = new LiveAPI(clipPath);
    try {
        clip.call("remove_warp_marker", beatTime);
    } catch (e) {
        throw "remove_warp_marker is not available on this clip";
    }
    return { deleted: true, beat_time: beatTime };
}

function cmd_convert_clip_time(params) {
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    var beatTime = param(params, "beat_time", null);
    var sampleTime = param(params, "sample_time", null);
    if (beatTime === null && sampleTime === null) throw "convert_clip_time requires beat_time or sample_time";
    var result = {};
    if (beatTime !== null) {
        try {
            result.beat_time = Number(beatTime);
            result.sample_time = unwrapNum(clip.call("beat_to_sample_time", Number(beatTime)));
        } catch (e) {
            throw "beat_to_sample_time is not available on this clip";
        }
    } else {
        try {
            result.sample_time = Number(sampleTime);
            result.beat_time = unwrapNum(clip.call("sample_to_beat_time", Number(sampleTime)));
        } catch (e) {
            throw "sample_to_beat_time is not available on this clip";
        }
    }
    return result;
}

function cmd_set_clip_color(params) {
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    return setColorFields(clip, clipPath, params, "clip");
}

function cmd_set_clip_muted(params) {
    var clipPath = sessionClipPath(params);
    var muted = param(params, "muted", true);
    var clip = new LiveAPI(clipPath);
    try {
        clip.set("muted", muted ? 1 : 0);
    } catch (e) {
        throw "muted is not available on this clip";
    }
    return { muted: apiGetOptionalNum(clipPath, "muted") ? true : false };
}

function cmd_set_clip_markers(params) {
    var clipPath = sessionClipPath(params);
    var startMarker = param(params, "start_marker", null);
    var endMarker = param(params, "end_marker", null);
    if (startMarker === null && endMarker === null) throw "set_clip_markers requires start_marker and/or end_marker";
    var clip = new LiveAPI(clipPath);
    try {
        if (endMarker !== null) clip.set("end_marker", Number(endMarker));
        if (startMarker !== null) clip.set("start_marker", Number(startMarker));
    } catch (e) {
        throw "start_marker/end_marker are not available on this clip";
    }
    return {
        start_marker: apiGetOptionalNum(clipPath, "start_marker"),
        end_marker: apiGetOptionalNum(clipPath, "end_marker")
    };
}

function cmd_set_clip_signature(params) {
    var clipPath = sessionClipPath(params);
    var numerator = param(params, "numerator", null);
    var denominator = param(params, "denominator", null);
    if (numerator === null && denominator === null) throw "set_clip_signature requires numerator and/or denominator";
    var clip = new LiveAPI(clipPath);
    try {
        if (numerator !== null) clip.set("signature_numerator", Math.floor(Number(numerator)));
        if (denominator !== null) clip.set("signature_denominator", Math.floor(Number(denominator)));
    } catch (e) {
        throw "clip time signature is not available on this clip";
    }
    return {
        numerator: apiGetOptionalNum(clipPath, "signature_numerator"),
        denominator: apiGetOptionalNum(clipPath, "signature_denominator")
    };
}

function cmd_quantize_pitch(params) {
    var clipPath = sessionClipPath(params);
    var pitch = Math.floor(Number(param(params, "pitch", 0)));
    var grid = param(params, "grid", 5);
    var strength = param(params, "strength", 1.0);
    var clip = new LiveAPI(clipPath);
    try {
        clip.call("quantize_pitch", pitch, grid, strength);
    } catch (e) {
        throw "quantize_pitch is not available on this clip";
    }
    return { quantized: true, pitch: pitch, grid: grid, strength: strength };
}

function cmd_set_clip_ram_mode(params) {
    var clipPath = sessionClipPath(params);
    var ramMode = param(params, "ram_mode", true);
    var clip = new LiveAPI(clipPath);
    try {
        clip.set("ram_mode", ramMode ? 1 : 0);
    } catch (e) {
        throw "ram_mode is not available on this clip";
    }
    return { ram_mode: apiGetOptionalNum(clipPath, "ram_mode") ? true : false };
}

function cmd_tap_tempo() {
    var song = new LiveAPI("live_set");
    try {
        song.call("tap_tempo");
    } catch (e) {
        throw "tap_tempo is not available";
    }
    return { tempo: apiGetNum("live_set", "tempo") };
}

function cmd_jump_by(params) {
    var beats = Number(param(params, "beats", 0));
    var song = new LiveAPI("live_set");
    try {
        song.call("jump_by", beats);
    } catch (e) {
        throw "jump_by is not available";
    }
    return { jumped_by: beats, current_song_time: apiGetNum("live_set", "current_song_time") };
}

function cmd_continue_playing() {
    var song = new LiveAPI("live_set");
    try {
        song.call("continue_playing");
    } catch (e) {
        throw "continue_playing is not available";
    }
    var playing = apiGetOptionalNum("live_set", "is_playing");
    return { continued: true, is_playing: playing !== null ? (playing ? true : false) : true };
}

function cmd_set_session_record(params) {
    var on = param(params, "on", true);
    var song = new LiveAPI("live_set");
    try {
        song.set("session_record", on ? 1 : 0);
    } catch (e) {
        throw "session_record is not available";
    }
    return { session_record: apiGetOptionalNum("live_set", "session_record") ? true : false };
}

function cmd_set_session_automation_record(params) {
    var on = param(params, "on", true);
    var song = new LiveAPI("live_set");
    try {
        song.set("session_automation_record", on ? 1 : 0);
    } catch (e) {
        throw "session_automation_record is not available";
    }
    return { session_automation_record: apiGetOptionalNum("live_set", "session_automation_record") ? true : false };
}

function cmd_re_enable_automation() {
    var song = new LiveAPI("live_set");
    try {
        song.call("re_enable_automation");
    } catch (e) {
        throw "re_enable_automation is not available";
    }
    return { re_enabled: true };
}

function cmd_set_count_in_duration(params) {
    var bars = Math.floor(Number(param(params, "bars", 1)));
    var song = new LiveAPI("live_set");
    try {
        song.set("count_in_duration", bars);
    } catch (e) {
        throw "count_in_duration is not available";
    }
    return { count_in_duration: apiGetOptionalNum("live_set", "count_in_duration") };
}

function cmd_set_exclusive_arm(params) {
    var on = param(params, "on", true);
    var song = new LiveAPI("live_set");
    try {
        song.set("exclusive_arm", on ? 1 : 0);
    } catch (e) {
        throw "exclusive_arm is not available";
    }
    return { exclusive_arm: apiGetOptionalNum("live_set", "exclusive_arm") ? true : false };
}

function cmd_set_punch(params) {
    var punchIn = param(params, "punch_in", null);
    var punchOut = param(params, "punch_out", null);
    if (punchIn === null && punchOut === null) throw "set_punch requires punch_in and/or punch_out";
    var song = new LiveAPI("live_set");
    try {
        if (punchIn !== null) song.set("punch_in", punchIn ? 1 : 0);
        if (punchOut !== null) song.set("punch_out", punchOut ? 1 : 0);
    } catch (e) {
        throw "punch_in/punch_out are not available";
    }
    return {
        punch_in: apiGetOptionalNum("live_set", "punch_in") ? true : false,
        punch_out: apiGetOptionalNum("live_set", "punch_out") ? true : false
    };
}

function cmd_set_song_scale(params) {
    var scaleName = param(params, "scale_name", null);
    var rootNote = param(params, "root_note", null);
    if (scaleName === null && rootNote === null) throw "set_song_scale requires scale_name and/or root_note";
    var song = new LiveAPI("live_set");
    if (scaleName !== null) {
        try {
            song.set("scale_name", String(scaleName));
        } catch (e) {
            throw "scale_name is not available";
        }
    }
    if (rootNote !== null) {
        try {
            song.set("root_note", Math.floor(Number(rootNote)));
        } catch (e) {
            throw "root_note is not available";
        }
    }
    var result = {};
    var name = apiGetOptionalStr("live_set", "scale_name");
    var root = apiGetOptionalNum("live_set", "root_note");
    if (name !== null) result.scale_name = name;
    if (root !== null) result.root_note = root;
    return result;
}

function cmd_set_track_color(params) {
    var trackIndex = param(params, "track_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    if (!track.id || track.id === "0") throw "Track index out of range";
    return setColorFields(track, trackPath, params, "track");
}

function cmd_set_scene_color(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var scenePath = "live_set scenes " + sceneIndex;
    var scene = new LiveAPI(scenePath);
    if (!scene.id || scene.id === "0") throw "Scene index out of range";
    return setColorFields(scene, scenePath, params, "scene");
}

function cmd_duplicate_scene(params) {
    var index = param(params, "scene_index", param(params, "index", 0));
    var song = new LiveAPI("live_set");
    try {
        song.call("duplicate_scene", index);
    } catch (e) {
        throw "duplicate_scene failed";
    }
    return {
        duplicated: true,
        scene_index: index,
        scene_count: apiGetCount("live_set", "scenes")
    };
}

function cmd_set_scene_tempo(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var tempo = Number(param(params, "tempo", 0));
    var scenePath = "live_set scenes " + sceneIndex;
    var scene = new LiveAPI(scenePath);
    if (!scene.id || scene.id === "0") throw "Scene index out of range";
    try {
        scene.set("tempo", tempo);
    } catch (e) {
        throw "scene.tempo is not available";
    }
    try {
        scene.set("tempo_enabled", tempo > 0 ? 1 : 0);
    } catch (e2) {}
    return {
        scene_index: sceneIndex,
        tempo: apiGetOptionalNum(scenePath, "tempo")
    };
}

function cmd_set_scene_signature(params) {
    var sceneIndex = param(params, "scene_index", 0);
    var numerator = param(params, "numerator", null);
    var denominator = param(params, "denominator", null);
    if (numerator === null && denominator === null) throw "set_scene_signature requires numerator and/or denominator";
    var scenePath = "live_set scenes " + sceneIndex;
    var scene = new LiveAPI(scenePath);
    if (!scene.id || scene.id === "0") throw "Scene index out of range";
    function setSig(prop, value) {
        try {
            scene.set(prop, Math.floor(Number(value)));
            return true;
        } catch (e) {
            return false;
        }
    }
    if (numerator !== null) {
        if (!setSig("time_signature_numerator", numerator) && !setSig("signature_numerator", numerator)) {
            throw "scene time signature numerator is not available";
        }
    }
    if (denominator !== null) {
        if (!setSig("time_signature_denominator", denominator) && !setSig("signature_denominator", denominator)) {
            throw "scene time signature denominator is not available";
        }
    }
    try {
        scene.set("time_signature_enabled", 1);
    } catch (e3) {}
    var result = { scene_index: sceneIndex };
    var n = apiGetOptionalNum(scenePath, "time_signature_numerator");
    if (n === null) n = apiGetOptionalNum(scenePath, "signature_numerator");
    var d = apiGetOptionalNum(scenePath, "time_signature_denominator");
    if (d === null) d = apiGetOptionalNum(scenePath, "signature_denominator");
    if (n !== null) result.numerator = n;
    if (d !== null) result.denominator = d;
    return result;
}

function cmd_set_cue_volume(params) {
    var volume = Number(param(params, "volume", 0.85));
    var actual = setNormalizedMixerParam("live_set master_track mixer_device cue_volume", volume, "Cue volume");
    return {
        cue_volume: actual,
        normalized_value: volume
    };
}

// ─── Shared high-impact Live 12 API commands ───

function liveValue(raw) {
    if (raw instanceof Array) return raw.length ? raw[0] : null;
    return raw;
}

function integerParam(value, label, minimum) {
    if (value === null || value === undefined || value === "") throw label + " is required";
    var number = Number(value);
    if (!isFinite(number) || Math.floor(number) !== number ||
        (minimum !== undefined && number < minimum)) {
        throw label + " must be an integer" + (minimum !== undefined ? " >= " + minimum : "");
    }
    return number;
}

function requireLiveVersion(minMajor, minMinor, message) {
    var parts = liveVersion().split(".");
    var major = Number(parts[0]);
    var minor = Number(parts[1]);
    if (!isFinite(major) || !isFinite(minor) || major < minMajor ||
        (major === minMajor && minor < minMinor)) {
        throw message + " (running Live " + parts.join(".") + ")";
    }
}

function cmd_get_application_info() {
    var app = new LiveAPI("live_app");
    var major = Number(liveValue(app.call("get_major_version")));
    var minor = Number(liveValue(app.call("get_minor_version")));
    var bugfix = Number(liveValue(app.call("get_bugfix_version")));
    var version;
    try {
        version = String(liveValue(app.call("get_version_string")));
    } catch (e) {
        version = major + "." + minor + "." + bugfix;
    }
    var result = {
        major_version: major,
        minor_version: minor,
        bugfix_version: bugfix,
        version: version
    };
    var dialogMessage = apiGetOptionalStr("live_app", "current_dialog_message");
    var buttonCount = apiGetOptionalNum("live_app", "current_dialog_button_count");
    var openCount = apiGetOptionalNum("live_app", "open_dialog_count");
    if (dialogMessage !== null) result.current_dialog_message = dialogMessage;
    if (buttonCount !== null) result.current_dialog_button_count = buttonCount;
    if (openCount !== null) result.open_dialog_count = openCount;
    return result;
}

function cmd_press_current_dialog_button(params) {
    var index = integerParam(param(params, "index", null), "index", 0);
    var buttonCount = apiGetOptionalNum("live_app", "current_dialog_button_count");
    if (buttonCount === null) {
        throw "current dialog button count is unavailable; press_current_dialog_button is not supported by this Live version";
    }
    buttonCount = Math.floor(buttonCount);
    if (index >= buttonCount) {
        throw "Dialog button index out of range: " + index + " (button count " + buttonCount + ")";
    }
    var app = new LiveAPI("live_app");
    try {
        app.call("press_current_dialog_button", index);
    } catch (e) {
        throw "press_current_dialog_button failed: " + e;
    }
    return { pressed: true, index: index };
}

function rackDevice(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = param(params, "device_index", 0);
    var path = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var device = new LiveAPI(path);
    if (!device.id || device.id === "0") throw "Device index out of range";
    return {
        track_index: trackIndex,
        device_index: deviceIndex,
        path: path,
        api: device
    };
}

function rackMacroState(info) {
    var path = info.path;
    var device = info.api;
    var mappedList = null;
    try {
        mappedList = asBoolList(device.get("macros_mapped"));
    } catch (e) {
        mappedList = null;
    }
    var hasMappings = apiGetOptionalNum(path, "has_macro_mappings");
    var visible = apiGetOptionalNum(path, "visible_macro_count");
    var variationCount = apiGetOptionalNum(path, "variation_count");
    var selectedVariation = apiGetOptionalNum(path, "selected_variation_index");
    var parameterCount = apiGetOptionalCount(path, "parameters");
    var macros = [];
    for (var i = 0; i < parameterCount; i++) {
        var parameterPath = path + " parameters " + i;
        var name = apiGetOptionalStr(parameterPath, "name") || "";
        var originalName = apiGetOptionalStr(parameterPath, "original_name");
        var macroName = originalName || name;
        if (String(macroName).indexOf("Macro") !== 0) continue;
        var macroNumber = macroNumberFromName(macroName);
        if (mappedList) {
            if (macroNumber === null || !mappedList[macroNumber - 1]) continue;
        } else if (visible !== null && macroNumber !== null && macroNumber > visible) {
            continue;
        }
        macros.push({
            index: i,
            name: name,
            original_name: originalName,
            value: apiGetOptionalNum(parameterPath, "value")
        });
    }
    var result = {
        track_index: info.track_index,
        device_index: info.device_index,
        macros: macros,
        visible_macro_count: visible,
        variation_count: variationCount,
        selected_variation_index: selectedVariation
    };
    if (mappedList) {
        result.macros_mapped = mappedList;
        result.mapped_macros = macros;
    }
    if (hasMappings !== null) result.has_macro_mappings = hasMappings ? true : false;
    return result;
}

function rackMutation(params, method, operation) {
    var info = rackDevice(params);
    try {
        info.api.call(method);
    } catch (e) {
        throw operation + " failed (requires a RackDevice and Live 11+): " + e;
    }
    var result = rackMacroState(info);
    result.operation = operation;
    return result;
}

function cmd_add_macro(params) {
    return rackMutation(params, "add_macro", "add_macro");
}

function cmd_remove_macro(params) {
    return rackMutation(params, "remove_macro", "remove_macro");
}

function cmd_randomize_macros(params) {
    return rackMutation(params, "randomize_macros", "randomize_macros");
}

function cmd_store_macro_variation(params) {
    return rackMutation(params, "store_variation", "store_macro_variation");
}

function variationMutation(params, method, operation) {
    var info = rackDevice(params);
    var variationIndex = integerParam(param(params, "variation_index", null), "variation_index", 0);
    var count = apiGetOptionalNum(info.path, "variation_count");
    if (count !== null && variationIndex >= count) {
        throw "Variation index out of range: " + variationIndex + " (variation count " + count + ")";
    }
    try {
        info.api.set("selected_variation_index", variationIndex);
        info.api.call(method);
    } catch (e) {
        throw operation + " failed (requires a RackDevice and Live 11+): " + e;
    }
    var result = rackMacroState(info);
    result.operation = operation;
    result.variation_index = variationIndex;
    return result;
}

function cmd_recall_macro_variation(params) {
    return variationMutation(params, "recall_selected_variation", "recall_macro_variation");
}

function cmd_delete_macro_variation(params) {
    return variationMutation(params, "delete_selected_variation", "delete_macro_variation");
}

function cmd_duplicate_clip_to_arrangement(params) {
    var trackIndex = param(params, "track_index", 0);
    var clipIndex = integerParam(param(params, "clip_index", 0), "clip_index", 0);
    var destinationValue = param(params, "destination_time", null);
    if (destinationValue === null || destinationValue === undefined) throw "destination_time is required";
    var destinationTime = Number(destinationValue);
    if (!isFinite(destinationTime) || destinationTime < 0) throw "destination_time must be a finite number >= 0";

    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    if (!track.id || track.id === "0") throw "Track index out of range";
    var slotPath = trackPath + " clip_slots " + clipIndex;
    if (!apiGetNum(slotPath, "has_clip")) throw "No clip in source slot " + clipIndex;
    var clip = new LiveAPI(slotPath + " clip");
    var before = apiGetOptionalCount(trackPath, "arrangement_clips");
    try {
        track.call("duplicate_clip_to_arrangement", "id " + clip.id, destinationTime);
    } catch (e) {
        throw "duplicate_clip_to_arrangement failed (Track.duplicate_clip_to_arrangement requires Live 11+): " + e;
    }
    var after = apiGetOptionalCount(trackPath, "arrangement_clips");
    return {
        track_index: trackIndex,
        clip_index: clipIndex,
        destination_time: destinationTime,
        arrangement_clip_count_before: before,
        arrangement_clip_count: after,
        duplicated: true
    };
}

function cmd_insert_device(params) {
    requireLiveVersion(12, 3,
        "insert_device requires Live 12.3+ and a native Live device; VST/AU and Max devices are not supported");
    var trackIndex = param(params, "track_index", 0);
    var deviceName = String(param(params, "device_name", ""));
    var targetValue = param(params, "target_index", null);
    if (!deviceName) throw "device_name is required";
    var targetIndex = targetValue === null || targetValue === undefined
        ? null : integerParam(targetValue, "target_index", 0);
    var trackPath = getTrackPath(trackIndex);
    var track = new LiveAPI(trackPath);
    if (!track.id || track.id === "0") throw "Track index out of range";
    var before = apiGetOptionalCount(trackPath, "devices");
    try {
        if (targetIndex === null) track.call("insert_device", deviceName);
        else track.call("insert_device", deviceName, targetIndex);
    } catch (e) {
        throw "insert_device failed (Live 12.3+ native devices only; VST/AU and Max devices require browser/.adg workflows): " + e;
    }
    var after = apiGetOptionalCount(trackPath, "devices");
    return {
        track_index: trackIndex,
        device_name: deviceName,
        target_index: targetIndex,
        device_count_before: before,
        device_count: after,
        inserted: true
    };
}

function simplerDevice(params) {
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = integerParam(param(params, "device_index", 0), "device_index", 0);
    var path = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var device = new LiveAPI(path);
    if (!device.id || device.id === "0") throw "Device index out of range";
    var className = apiGetOptionalStr(path, "class_name") || "";
    var displayName = apiGetOptionalStr(path, "class_display_name") || "";
    if (String(className).toLowerCase().indexOf("simpler") < 0 &&
        String(displayName).toLowerCase().indexOf("simpler") < 0) {
        throw "Device is not Simpler";
    }
    var samplePath = path + " sample";
    var sample = new LiveAPI(samplePath);
    if (!sample.id || sample.id === "0") throw "Simpler has no accessible sample";
    return {
        track_index: trackIndex,
        device_index: deviceIndex,
        device_path: path,
        device: device,
        sample_path: samplePath,
        sample: sample
    };
}

function sampleInfo(info) {
    return {
        track_index: info.track_index,
        device_index: info.device_index,
        file_path: apiGetOptionalStr(info.sample_path, "file_path"),
        start_marker: apiGetOptionalNum(info.sample_path, "start_marker") === null
            ? null : Math.floor(apiGetOptionalNum(info.sample_path, "start_marker")),
        end_marker: apiGetOptionalNum(info.sample_path, "end_marker") === null
            ? null : Math.floor(apiGetOptionalNum(info.sample_path, "end_marker"))
    };
}

function cmd_get_simpler_sample(params) {
    return sampleInfo(simplerDevice(params));
}

function cmd_set_simpler_sample_window(params) {
    var info = simplerDevice(params);
    var startValue = param(params, "start_marker", null);
    var endValue = param(params, "end_marker", null);
    if (startValue === null && endValue === null) {
        throw "set_simpler_sample_window requires start_marker and/or end_marker";
    }
    try {
        if (startValue !== null) info.sample.set("start_marker", integerParam(startValue, "start_marker", 0));
        if (endValue !== null) info.sample.set("end_marker", integerParam(endValue, "end_marker", 0));
    } catch (e) {
        throw "set_simpler_sample_window failed (sample markers are integer sample frames): " + e;
    }
    return sampleInfo(info);
}

function cmd_replace_simpler_sample(params) {
    requireLiveVersion(12, 4, "replace_simpler_sample requires Live 12.4+ and SimplerDevice.replace_sample");
    var info = simplerDevice(params);
    var filePath = String(param(params, "file_path", ""));
    if (!filePath) throw "file_path is required";
    try {
        info.device.call("replace_sample", filePath);
    } catch (e) {
        throw "replace_simpler_sample failed (SimplerDevice.replace_sample requires Live 12.4+): " + e;
    }
    return sampleInfo(info);
}

function mergeNoteDictionary(base, patch) {
    var merged = {};
    var key;
    for (key in base) {
        if (base.hasOwnProperty(key)) merged[key] = base[key];
    }
    for (key in patch) {
        if (patch.hasOwnProperty(key)) merged[key] = patch[key];
    }
    return merged;
}

function cmd_apply_note_modifications(params) {
    var notes = param(params, "notes", null);
    if (!Array.isArray(notes)) throw "notes must be an array of note dictionaries";
    var clipPath = sessionClipPath(params);
    var clip = new LiveAPI(clipPath);
    if (!apiGetNum(clipPath, "is_midi_clip")) throw "Not a MIDI clip";
    if (!notes.length) return { track_index: param(params, "track_index", 0), modified_note_count: 0 };

    var current = readAllNotes(clip, apiGetNum(clipPath, "length"));
    var byId = {};
    for (var i = 0; i < current.length; i++) {
        if (current[i].note_id === undefined || current[i].note_id === null) {
            throw "Note IDs are unavailable; apply_note_modifications requires Live 11+ get_notes_extended data";
        }
        byId[String(current[i].note_id)] = current[i];
    }

    var mergedNotes = [];
    var mergedById = {};
    for (i = 0; i < notes.length; i++) {
        var patch = notes[i];
        if (!patch || typeof patch !== "object") throw "Each note modification must be a dictionary";
        var noteId = integerParam(patch.note_id, "note_id", 0);
        var key = String(noteId);
        if (!byId.hasOwnProperty(key)) throw "Note ID not found in clip: " + noteId;
        var merged = mergeNoteDictionary(byId[key], patch);
        merged.note_id = noteId;
        if (mergedById.hasOwnProperty(key)) mergedNotes[mergedById[key]] = merged;
        else {
            mergedById[key] = mergedNotes.length;
            mergedNotes.push(merged);
        }
    }

    try {
        clip.call("apply_note_modifications", { notes: mergedNotes });
    } catch (e) {
        throw "apply_note_modifications failed (requires a MIDI clip and Live 11+): " + e;
    }
    var result = {
        track_index: param(params, "track_index", 0),
        clip_index: param(params, "clip_index", 0),
        modified_note_count: mergedNotes.length,
        note_count: current.length,
        applied: true
    };
    var arrangementIndex = param(params, "arrangement_clip_index", null);
    if (arrangementIndex !== null && arrangementIndex !== undefined) {
        result.arrangement_clip_index = arrangementIndex;
    }
    return result;
}
