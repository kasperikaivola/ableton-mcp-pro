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


// Focused command modules loaded into the shared Max JS global scope.
include("lom-core.js");
include("lom-read.js");
include("lom-session.js");
include("lom-clips.js");
include("lom-devices.js");
include("lom-routing.js");
include("lom-mixer.js");
include("lom-detail.js");
include("lom-live12.js");

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
        case "load_drum_pad_sample": return cmd_load_drum_pad_sample(params);
        case "press_current_dialog_button": return cmd_press_current_dialog_button(params);
        case "load_instrument_or_effect": return cmd_load_instrument_or_effect(params);
        case "load_browser_item": return cmd_load_instrument_or_effect(params);
        case "set_clip_envelope": return cmd_set_clip_envelope(params);
        case "clear_clip_envelope": return cmd_clear_clip_envelope(params);

        default:
            throw "Unknown command: " + cmdType;
    }
}
