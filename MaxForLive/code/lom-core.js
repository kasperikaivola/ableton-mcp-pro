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

