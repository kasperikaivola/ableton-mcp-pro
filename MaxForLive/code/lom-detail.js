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
