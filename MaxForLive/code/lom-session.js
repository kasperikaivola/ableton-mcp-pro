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
