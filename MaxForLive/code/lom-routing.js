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
