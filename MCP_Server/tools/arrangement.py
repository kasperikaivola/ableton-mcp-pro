import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def delete_arrangement_clip(ctx: Context, track_index: int, arrangement_clip_index: int) -> str:
    """
    Delete a clip from the arrangement view by track + index.

    Parameters:
    - track_index: Index of the track
    - arrangement_clip_index: Index into track.arrangement_clips (0 = first clip)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_arrangement_clip", {
            "track_index": track_index,
            "arrangement_clip_index": arrangement_clip_index,
        })
        return f"Deleted arrangement clip {result.get('deleted_index')} on track {track_index} ({result.get('remaining_count', 0)} remaining)"
    except Exception as e:
        logger.error(f"Error deleting arrangement clip: {str(e)}")
        return f"Error deleting arrangement clip: {str(e)}"

@mcp.tool()
def create_arrangement_midi_clip(
    ctx: Context,
    track_index: int,
    time: float,
    length: float,
    notes: Optional[List[Dict[str, Union[int, float, bool]]]] = None,
) -> str:
    """
    Create a MIDI clip directly in the arrangement view at a given position.
    Optionally seed it with notes in one call.
    Requires Live 11+ (uses Track.create_midi_clip API).

    Parameters:
    - track_index: Index of a MIDI track
    - time: Arrangement position in beats where the clip should start
    - length: Clip length in beats (e.g. 32.0 = 8 bars at 4/4)
    - notes: Optional list of {pitch, start_time, duration, velocity, mute?} dicts.
             Note start_times are relative to the clip's start.
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "time": time,
            "length": length,
        }
        if notes is not None:
            params["notes"] = notes
        result = ableton.send_command("create_arrangement_midi_clip", params)
        return (
            f"Created arrangement MIDI clip on track {track_index} "
            f"at beat {result.get('start_time', time)} "
            f"(length: {result.get('length', length)} beats, "
            f"notes: {result.get('note_count', 0)}, "
            f"arrangement_clip_index: {result.get('arrangement_clip_index', -1)})"
        )
    except Exception as e:
        logger.error(f"Error creating arrangement MIDI clip: {str(e)}")
        return f"Error creating arrangement MIDI clip: {str(e)}"

@mcp.tool()
def create_arrangement_audio_clip(
    ctx: Context,
    track_index: int,
    file_path: str,
    time: float,
    length: Optional[float] = None,
    start_offset: Optional[float] = None,
) -> str:
    """
    Create an audio clip in the arrangement view at a given position. This is the only way to
    get a sample into Live over the socket (session slots cannot take a file path).
    Requires Live 11+ (uses Track.create_audio_clip API).

    Parameters:
    - track_index: Index of an audio track
    - file_path: Absolute path to an audio file (wav, aiff, flac, mp3, etc.)
    - time: Arrangement position in beats where the clip should start
    - length: Optional clip length in beats. If omitted, the file's natural length is used.
    - start_offset: Optional beats to skip at the head of the sample (preroll before a hit)
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "file_path": file_path,
            "time": time,
        }
        if length is not None:
            params["length"] = length
        if start_offset is not None:
            params["start_offset"] = start_offset
        result = ableton.send_command("create_arrangement_audio_clip", params)
        return (
            f"Created arrangement audio clip '{result.get('name', '')}' "
            f"on track {track_index} at beat {result.get('start_time', time)} "
            f"(length: {result.get('length', 0)} beats)"
        )
    except Exception as e:
        logger.error(f"Error creating arrangement audio clip: {str(e)}")
        return f"Error creating arrangement audio clip: {str(e)}"

@mcp.tool()
def get_arrangement_info(ctx: Context) -> str:
    """Get current arrangement state including song time, record mode, loop settings, and transport status."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement info: {str(e)}")
        return f"Error getting arrangement info: {str(e)}"

@mcp.tool()
def get_arrangement_clips(ctx: Context, track_index: int) -> str:
    """
    Get arrangement clips for a track. Shows what clips are in the arrangement timeline.
    Use track_index -1 for master track.

    Parameters:
    - track_index: The index of the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_clips", {
            "track_index": track_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement clips: {str(e)}")
        return f"Error getting arrangement clips: {str(e)}"

@mcp.tool()
def record_arrangement(ctx: Context, sections: List[dict], start_time: float = 0.0) -> str:
    """
    Record session clips into the arrangement by firing scenes at timed intervals.
    This runs inside Ableton for precise timing. Handles seeking, recording, and stopping automatically.

    Parameters:
    - sections: List of {"scene_index": int, "bars": int} defining each section.
                Example: [{"scene_index": 0, "bars": 8}, {"scene_index": 1, "bars": 8}, {"scene_index": 2, "bars": 16}]
    - start_time: Arrangement position in beats to begin recording from. Default 0
                  (beginning). Use this to append a new section past existing material.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("record_arrangement", {
            "sections": sections,
            "start_time": start_time
        })
        total_bars = result.get("total_bars", 0)
        tempo = result.get("tempo", 120)
        recorded = result.get("sections", [])
        summary = []
        for s in recorded:
            summary.append(f"  Bars {s['start_bar']}-{s['end_bar']}: Scene {s['scene_index']} ({s['scene_name']}) [{s['bars']} bars]")
        return f"Recorded {total_bars} bars at {tempo} BPM:\n" + "\n".join(summary)
    except Exception as e:
        logger.error(f"Error recording arrangement: {str(e)}")
        return f"Error recording arrangement: {str(e)}"

@mcp.tool()
def get_full_arrangement(ctx: Context) -> str:
    """
    Get a complete view of the arrangement — all tracks with their arrangement clips,
    song tempo, time signature, length, and scene list.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_full_arrangement", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting full arrangement: {str(e)}")
        return f"Error getting full arrangement: {str(e)}"

@mcp.tool()
def create_arrangement_audio_clips_batch(ctx: Context, track_index: int, file_path: str, times: List[float],
                                         length: Optional[float] = None, start_offset: Optional[float] = None) -> str:
    """Place the same sample at many beat positions on one audio track in a single call
    (32 kicks in one round trip instead of 32). length/start_offset apply to every placement."""
    try:
        params = {"track_index": track_index, "file_path": file_path, "times": times}
        if length is not None: params["length"] = length
        if start_offset is not None: params["start_offset"] = start_offset
        result = get_ableton_connection().send_command("create_arrangement_audio_clips_batch", params)
        failed = result.get("failed_count", 0)
        return f"Placed {result.get('placed_count', 0)}/{len(times)} clips of '{file_path.split('/')[-1]}' on track {track_index}" + (f" ({failed} failed)" if failed else "")
    except Exception as e:
        logger.error(f"Error batch-placing arrangement audio clips: {str(e)}")
        return f"Error batch-placing arrangement audio clips: {str(e)}"

@mcp.tool()
def resample_master(ctx: Context, seconds: Optional[float] = None, name: str = "master rec", start_time: float = 0.0) -> str:
    """Record the main mix to an audio file: creates an audio track on Resampling, arms only it,
    plays the arrangement from start_time with record mode on until the last clip ends (or
    `seconds`), then returns the recorded file's path. Blocks for the whole song. Live has no
    export command, so this is how an agent gets a mixdown out."""
    try:
        params = {"name": name, "start_time": start_time}
        if seconds is not None: params["seconds"] = seconds
        result = get_ableton_connection().send_command("resample_master", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error resampling master: {str(e)}")
        return f"Error resampling master: {str(e)}"

# Main execution

