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
