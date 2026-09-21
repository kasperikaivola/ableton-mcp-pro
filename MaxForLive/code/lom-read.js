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
