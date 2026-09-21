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
