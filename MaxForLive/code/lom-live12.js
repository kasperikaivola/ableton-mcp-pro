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

function cmd_load_drum_pad_sample(params) {
    requireLiveVersion(12, 4, "load_drum_pad_sample requires Live 12.4+");
    var trackIndex = param(params, "track_index", 0);
    var deviceIndex = integerParam(param(params, "device_index", 0), "device_index", 0);
    var note = integerParam(param(params, "note", null), "note", 0);
    if (note > 127) throw "note must be between 0 and 127";
    var filePath = String(param(params, "file_path", ""));
    if (!filePath) throw "file_path is required";
    var name = param(params, "name", null);
    var rackPath = getTrackPath(trackIndex) + " devices " + deviceIndex;
    var rack = new LiveAPI(rackPath);
    if (!rack.id || rack.id === "0") throw "Device index out of range";
    if (!apiGetOptionalNum(rackPath, "can_have_drum_pads")) throw "Device is not a top-level Drum Rack";

    var padPath = null;
    var padCount = apiGetOptionalCount(rackPath, "drum_pads");
    for (var i = 0; i < padCount; i++) {
        var candidate = rackPath + " drum_pads " + i;
        if (apiGetOptionalNum(candidate, "note") === note) {
            padPath = candidate;
            break;
        }
    }
    if (!padPath) throw "Drum Rack has no pad for MIDI note " + note;
    if (apiGetOptionalCount(padPath, "chains") > 0) throw "Drum Rack pad " + note + " is not empty";

    var chainIndex = apiGetOptionalCount(rackPath, "chains");
    try {
        rack.call("insert_chain", chainIndex);
        var chainPath = rackPath + " chains " + chainIndex;
        var chain = new LiveAPI(chainPath);
        chain.set("in_note", note);
        if (name !== null) chain.set("name", String(name));
        chain.call("insert_device", "Simpler");
        var simplerPath = chainPath + " devices " + (apiGetOptionalCount(chainPath, "devices") - 1);
        var simpler = new LiveAPI(simplerPath);
        simpler.call("replace_sample", filePath);
        return {
            track_index: trackIndex,
            device_index: deviceIndex,
            note: note,
            chain_index: chainIndex,
            chain_name: apiGetOptionalStr(chainPath, "name"),
            file_path: filePath,
            loaded: true
        };
    } catch (e) {
        try { new LiveAPI(padPath).call("delete_all_chains"); } catch (cleanupError) {}
        throw "load_drum_pad_sample failed: " + e;
    }
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
