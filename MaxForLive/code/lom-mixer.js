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
