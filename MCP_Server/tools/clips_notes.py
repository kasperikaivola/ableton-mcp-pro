import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def create_clip(ctx: Context, track_index: int, clip_index: int, length: float = 4.0) -> str:
    """
    Create a new MIDI clip in the specified track and clip slot.
    
    Parameters:
    - track_index: The index of the track to create the clip in
    - clip_index: The index of the clip slot to create the clip in
    - length: The length of the clip in beats (default: 4.0)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_clip", {
            "track_index": track_index, 
            "clip_index": clip_index, 
            "length": length
        })
        return f"Created new clip at track {track_index}, slot {clip_index} with length {length} beats"
    except Exception as e:
        logger.error(f"Error creating clip: {str(e)}")
        return f"Error creating clip: {str(e)}"

@mcp.tool()
def get_arrangement_clip_notes(ctx: Context, track_index: int, arrangement_clip_index: int) -> str:
    """
    Read MIDI notes from a clip in the arrangement view (not session view).

    Parameters:
    - track_index: Index of the track
    - arrangement_clip_index: Index into track.arrangement_clips (0 = first arrangement clip on the track).
                              Get the index from `get_arrangement_clips`.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_arrangement_clip_notes", {
            "track_index": track_index,
            "arrangement_clip_index": arrangement_clip_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting arrangement clip notes: {str(e)}")
        return f"Error getting arrangement clip notes: {str(e)}"

@mcp.tool()
def add_notes_to_clip(
    ctx: Context, 
    track_index: int, 
    clip_index: int, 
    notes: List[Dict[str, Union[int, float, bool]]],
    arrangement_clip_index: Optional[int] = None,
) -> str:
    """
    Add MIDI notes to a session clip or an arrangement clip.
    
    Parameters:
    - track_index: The track containing the target clip.
    - clip_index: The session clip-slot index. Used when arrangement_clip_index is omitted.
    - arrangement_clip_index: Optional index into the track's arrangement clips. When
                              provided, notes are added to that arrangement clip instead
                              of the session slot; clip_index is ignored.
    - notes: Note dictionaries with pitch, start_time, duration, velocity, and optional mute.
             start_time is relative to the beginning of the target clip.

    If arrangement_clip_index is omitted, this preserves the original session-clip
    behavior and response.
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes
        }
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        ableton.send_command("add_notes_to_clip", params)
        if arrangement_clip_index is None:
            return f"Added {len(notes)} notes to clip at track {track_index}, slot {clip_index}"
        return f"Added {len(notes)} notes to arrangement clip {arrangement_clip_index} on track {track_index}"
    except Exception as e:
        logger.error(f"Error adding notes to clip: {str(e)}")
        return f"Error adding notes to clip: {str(e)}"

@mcp.tool()
def set_clip_name(ctx: Context, track_index: int, clip_index: int, name: str) -> str:
    """
    Set the name of a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    - name: The new name for the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_clip_name", {
            "track_index": track_index,
            "clip_index": clip_index,
            "name": name
        })
        return f"Renamed clip at track {track_index}, slot {clip_index} to '{name}'"
    except Exception as e:
        logger.error(f"Error setting clip name: {str(e)}")
        return f"Error setting clip name: {str(e)}"

@mcp.tool()
def fire_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Start playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Started playing clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error firing clip: {str(e)}")
        return f"Error firing clip: {str(e)}"

@mcp.tool()
def stop_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Stop playing a clip.
    
    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot containing the clip
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Stopped clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error stopping clip: {str(e)}")
        return f"Error stopping clip: {str(e)}"

@mcp.tool()
def delete_clip(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Delete a clip from a clip slot.

    Parameters:
    - track_index: The index of the track containing the clip
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_clip", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return f"Deleted clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        logger.error(f"Error deleting clip: {str(e)}")
        return f"Error deleting clip: {str(e)}"

@mcp.tool()
def duplicate_clip(ctx: Context, track_index: int, clip_index: int, target_index: int = -1) -> str:
    """
    Duplicate a clip to another slot on the same track.

    Parameters:
    - track_index: The index of the track
    - clip_index: The source clip slot index
    - target_index: The target clip slot index (-1 to auto-find next empty slot)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "target_index": target_index
        })
        target = result.get("target_index", target_index)
        return f"Duplicated clip from slot {clip_index} to slot {target} on track {track_index}"
    except Exception as e:
        logger.error(f"Error duplicating clip: {str(e)}")
        return f"Error duplicating clip: {str(e)}"

@mcp.tool()
def duplicate_clip_to_arrangement(
    ctx: Context,
    track_index: int,
    clip_index: int,
    destination_time: float,
) -> str:
    """Duplicate a session clip slot to the same track's arrangement at a beat time.

    Uses Track.duplicate_clip_to_arrangement so MIDI/audio content and envelopes are copied;
    availability depends on the Live Remote Script backend exposing that API.
    """
    try:
        result = get_ableton_connection().send_command("duplicate_clip_to_arrangement", {
            "track_index": track_index,
            "clip_index": clip_index,
            "destination_time": destination_time,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error duplicating clip to arrangement: {str(e)}")
        return f"Error duplicating clip to arrangement: {str(e)}"

@mcp.tool()
def set_clip_loop(ctx: Context, track_index: int, clip_index: int, loop_start: float = None, loop_end: float = None, looping: bool = None) -> str:
    """
    Set clip loop settings. All parameters are optional — only provided values are changed.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    - loop_start: Loop start position in beats (optional)
    - loop_end: Loop end position in beats (optional)
    - looping: Whether the clip should loop (optional)
    """
    try:
        ableton = get_ableton_connection()
        params = {"track_index": track_index, "clip_index": clip_index}
        if loop_start is not None:
            params["loop_start"] = loop_start
        if loop_end is not None:
            params["loop_end"] = loop_end
        if looping is not None:
            params["looping"] = looping
        result = ableton.send_command("set_clip_loop", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip loop: {str(e)}")
        return f"Error setting clip loop: {str(e)}"

@mcp.tool()
def get_clip_notes(ctx: Context, track_index: int, clip_index: int) -> str:
    """
    Get all MIDI notes from a clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The index of the clip slot
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_clip_notes", {
            "track_index": track_index,
            "clip_index": clip_index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip notes: {str(e)}")
        return f"Error getting clip notes: {str(e)}"

@mcp.tool()
def apply_note_modifications(
    ctx: Context,
    track_index: int,
    clip_index: int,
    notes: List[Dict[str, Any]],
    arrangement_clip_index: Optional[int] = None,
) -> str:
    """Apply note patches to a session or arrangement MIDI clip.

    Each note dict must include the note_id returned by get_*_notes; omitted fields
    are preserved by the Remote Script backend. Times and duration are in beats.
    """
    try:
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes,
        }
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("apply_note_modifications", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error applying note modifications: {str(e)}")
        return f"Error applying note modifications: {str(e)}"

@mcp.tool()
def set_clip_envelope(ctx: Context, track_index: int, clip_index: int, device_index: int, parameter_index: int, points: List[dict], arrangement_clip_index: Optional[int] = None) -> str:
    """
    Set automation envelope points for a parameter in a session clip.

    Session clip envelopes work. Arrangement clip envelopes are a LOM limit:
    automation_envelope is session-only; arrangement automation is track-level and
    not in the public LOM. arrangement_clip_index is still forwarded; the Remote
    Script will error clearly on set.

    Parameters:
    - track_index: The index of the track
    - clip_index: The session clip-slot index. Used when arrangement_clip_index is omitted.
    - device_index: The index of the device
    - parameter_index: The index of the parameter
    - points: List of {"time": float, "value": float} where value is normalized 0.0-1.0
    - arrangement_clip_index: Optional index into the track's arrangement clips (same as
                              add_notes_to_clip). When provided, addresses that arrangement
                              MIDI/audio clip instead of the session slot.
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "device_index": device_index,
            "parameter_index": parameter_index,
            "points": points
        }
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = ableton.send_command("set_clip_envelope", params)
        return f"Set {result.get('points_set', 0)} automation points for '{result.get('parameter_name', '')}'"
    except Exception as e:
        logger.error(f"Error setting clip envelope: {str(e)}")
        return f"Error setting clip envelope: {str(e)}"

@mcp.tool()
def get_clip_envelope(ctx: Context, track_index: int, clip_index: int, device_index: int, parameter_index: int, arrangement_clip_index: Optional[int] = None) -> str:
    """
    Read automation envelope data for a parameter in a session clip.

    Session clip envelopes work. Arrangement clip envelopes are a LOM limit:
    automation_envelope is session-only; arrangement automation is track-level and
    not in the public LOM. arrangement_clip_index is still forwarded.

    Parameters:
    - track_index: The index of the track
    - clip_index: The session clip-slot index. Used when arrangement_clip_index is omitted.
    - device_index: The index of the device
    - parameter_index: The index of the parameter
    - arrangement_clip_index: Optional index into the track's arrangement clips (same as
                              add_notes_to_clip). When provided, addresses that arrangement
                              MIDI/audio clip instead of the session slot.
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "device_index": device_index,
            "parameter_index": parameter_index
        }
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = ableton.send_command("get_clip_envelope", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip envelope: {str(e)}")
        return f"Error getting clip envelope: {str(e)}"

@mcp.tool()
def clear_clip_envelope(ctx: Context, track_index: int, clip_index: int, device_index: int, parameter_index: int, arrangement_clip_index: Optional[int] = None) -> str:
    """
    Clear automation envelope for a parameter in a clip.

    Parameters:
    - track_index: The index of the track
    - clip_index: The session clip-slot index. Used when arrangement_clip_index is omitted.
    - device_index: The index of the device
    - parameter_index: The index of the parameter
    - arrangement_clip_index: Optional index into the track's arrangement clips (same as
                              add_notes_to_clip). When provided, addresses that arrangement
                              MIDI/audio clip instead of the session slot.
    """
    try:
        ableton = get_ableton_connection()
        params = {
            "track_index": track_index,
            "clip_index": clip_index,
            "device_index": device_index,
            "parameter_index": parameter_index
        }
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = ableton.send_command("clear_clip_envelope", params)
        return f"Cleared automation for '{result.get('parameter_name', '')}'"
    except Exception as e:
        logger.error(f"Error clearing clip envelope: {str(e)}")
        return f"Error clearing clip envelope: {str(e)}"

@mcp.tool()
def remove_notes(ctx: Context, track_index: int, clip_index: int, from_pitch: int = 0, pitch_span: int = 128,
                 from_time: float = 0.0, time_span: float = -1.0, arrangement_clip_index: int = None) -> str:
    """Remove the notes of a session MIDI clip inside a pitch/time window, leaving the rest intact.

    Parameters:
    - track_index, clip_index: the clip slot
    - from_pitch, pitch_span: pitch window (default: all pitches)
    - from_time, time_span: time window in beats (time_span -1 = to the end of the clip)
    """
    try:
        result = get_ableton_connection().send_command("remove_notes", {
            "track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "from_pitch": from_pitch,
            "pitch_span": pitch_span, "from_time": from_time, "time_span": time_span})
        return f"Removed {result.get('removed')} notes, {result.get('remaining')} remain"
    except Exception as e:
        logger.error(f"Error removing notes: {str(e)}")
        return f"Error removing notes: {str(e)}"

@mcp.tool()
def quantize_clip(ctx: Context, track_index: int, clip_index: int, grid: int = 5, strength: float = 1.0, arrangement_clip_index: int = None) -> str:
    """Quantize a session clip's notes to a grid.

    Parameters:
    - grid: Live's quantization enum: 1=1/4, 2=1/8, 3=1/8+1/8T, 4=1/8T, 5=1/16 (default), 6=1/16+1/16T, 7=1/16T, 8=1/32
    - strength: 0.0-1.0 (1.0 = snap fully)
    """
    try:
        get_ableton_connection().send_command("quantize_clip", {
            "track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "grid": grid, "strength": strength})
        return f"Quantized clip at track {track_index}, slot {clip_index} (grid {grid}, strength {strength})"
    except Exception as e:
        logger.error(f"Error quantizing clip: {str(e)}")
        return f"Error quantizing clip: {str(e)}"

@mcp.tool()
def duplicate_clip_loop(ctx: Context, track_index: int, clip_index: int, arrangement_clip_index: int = None) -> str:
    """Double a session clip's loop length and copy its contents into the new half."""
    try:
        result = get_ableton_connection().send_command("duplicate_clip_loop", {"track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index})
        return f"Loop doubled: length {result.get('length')} beats, loop {result.get('loop_start')}-{result.get('loop_end')}"
    except Exception as e:
        logger.error(f"Error duplicating clip loop: {str(e)}")
        return f"Error duplicating clip loop: {str(e)}"

@mcp.tool()
def duplicate_region(ctx: Context, track_index: int, clip_index: int, region_start: float, region_length: float,
                     destination_time: float, pitch: int = -1, transposition_amount: int = 0, arrangement_clip_index: int = None) -> str:
    """Copy a region of a session MIDI clip to another position, optionally one pitch only and/or transposed.

    Parameters:
    - region_start, region_length: source window in beats
    - destination_time: where the copy starts, in beats
    - pitch: only copy this pitch (-1 = all)
    - transposition_amount: semitones to transpose the copy
    """
    try:
        result = get_ableton_connection().send_command("duplicate_region", {
            "track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "region_start": region_start,
            "region_length": region_length, "destination_time": destination_time, "pitch": pitch,
            "transposition_amount": transposition_amount})
        return f"Duplicated region; clip length now {result.get('length')} beats"
    except Exception as e:
        logger.error(f"Error duplicating region: {str(e)}")
        return f"Error duplicating region: {str(e)}"

@mcp.tool()
def set_clip_gain(ctx: Context, track_index: int, clip_index: int, gain: float, arrangement_clip_index: int = None) -> str:
    """Set a session audio clip's gain, normalized 0.0-1.0 (0.4 is about 0 dB)."""
    try:
        result = get_ableton_connection().send_command("set_clip_gain", {"track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "gain": gain})
        return f"Clip gain {result.get('gain')} ({result.get('gain_display', '')})"
    except Exception as e:
        logger.error(f"Error setting clip gain: {str(e)}")
        return f"Error setting clip gain: {str(e)}"

@mcp.tool()
def set_clip_pitch(ctx: Context, track_index: int, clip_index: int, coarse: int = None, fine: int = None, arrangement_clip_index: int = None) -> str:
    """Transpose a session audio clip: coarse in semitones (-48..48), fine in cents (-500..500)."""
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index}
        if coarse is not None: params["coarse"] = coarse
        if fine is not None: params["fine"] = fine
        result = get_ableton_connection().send_command("set_clip_pitch", params)
        return f"Clip pitch: {result.get('pitch_coarse')} st, {result.get('pitch_fine')} cents"
    except Exception as e:
        logger.error(f"Error setting clip pitch: {str(e)}")
        return f"Error setting clip pitch: {str(e)}"

@mcp.tool()
def set_clip_warping(ctx: Context, track_index: int, clip_index: int, warping: bool, arrangement_clip_index: int = None) -> str:
    """Turn warping on or off for a session audio clip."""
    try:
        result = get_ableton_connection().send_command("set_clip_warping", {"track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "warping": warping})
        return f"Warping {'on' if result.get('warping') else 'off'}"
    except Exception as e:
        logger.error(f"Error setting clip warping: {str(e)}")
        return f"Error setting clip warping: {str(e)}"

@mcp.tool()
def set_clip_warp_mode(ctx: Context, track_index: int, clip_index: int, warp_mode: int, arrangement_clip_index: int = None) -> str:
    """Set a session audio clip's warp mode: 0=Beats, 1=Tones, 2=Texture, 3=Re-Pitch, 4=Complex, 6=Complex Pro."""
    try:
        result = get_ableton_connection().send_command("set_clip_warp_mode", {"track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index, "warp_mode": warp_mode})
        modes = {0: "Beats", 1: "Tones", 2: "Texture", 3: "Re-Pitch", 4: "Complex", 6: "Complex Pro"}
        return f"Warp mode {modes.get(result.get('warp_mode'), result.get('warp_mode'))}"
    except Exception as e:
        logger.error(f"Error setting clip warp mode: {str(e)}")
        return f"Error setting clip warp mode: {str(e)}"

@mcp.tool()
def get_clip_info(ctx: Context, track_index: int, clip_index: int = 0, arrangement_clip_index: int = None) -> str:
    """Read one clip's properties: length, loop points, start/end markers, mute, and for audio
    clips warping, warp mode, pitch, gain and file. Session slot, or an arrangement clip via arrangement_clip_index."""
    try:
        result = get_ableton_connection().send_command("get_clip_info", {
            "track_index": track_index, "clip_index": clip_index, "arrangement_clip_index": arrangement_clip_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting clip info: {str(e)}")
        return f"Error getting clip info: {str(e)}"

@mcp.tool()
def crop_clip(ctx: Context, track_index: int, clip_index: int, arrangement_clip_index: int = None) -> str:
    """Crop a clip to its loop start/end (clip.crop()).

    After crop, loop and markers are reset to the cropped clip (0..length).
    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("crop_clip", params)
        return f"Cropped clip; length {result.get('length', '')} beats"
    except Exception as e:
        logger.error(f"Error cropping clip: {str(e)}")
        return f"Error cropping clip: {str(e)}"

@mcp.tool()
def set_clip_launch(ctx: Context, track_index: int, clip_index: int, launch_mode: int = None,
                    launch_quantization: int = None, legato: bool = None, arrangement_clip_index: int = None) -> str:
    """Set session-clip launch behavior. Omit fields you do not want to change.

    Parameters:
    - launch_mode: 0=Trigger, 1=Gate, 2=Toggle, 3=Repeat
    - launch_quantization: Live enum (0 = none / follow global)
    - legato: keep playhead position on retrigger
    - arrangement_clip_index: optional arrangement clip, same as add_notes_to_clip
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if launch_mode is not None:
            params["launch_mode"] = launch_mode
        if launch_quantization is not None:
            params["launch_quantization"] = launch_quantization
        if legato is not None:
            params["legato"] = legato
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_launch", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip launch: {str(e)}")
        return f"Error setting clip launch: {str(e)}"

@mcp.tool()
def set_clip_color(ctx: Context, track_index: int, clip_index: int, color_index: int = None,
                   color: int = None, arrangement_clip_index: int = None) -> str:
    """Set a clip's color. Provide color_index (Live palette) and/or color (RGB int).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if color_index is not None:
            params["color_index"] = color_index
        if color is not None:
            params["color"] = color
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_color", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip color: {str(e)}")
        return f"Error setting clip color: {str(e)}"

@mcp.tool()
def set_clip_muted(ctx: Context, track_index: int, clip_index: int, muted: bool,
                   arrangement_clip_index: int = None) -> str:
    """Mute or unmute a clip.

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "muted": muted}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_muted", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip muted: {str(e)}")
        return f"Error setting clip muted: {str(e)}"

@mcp.tool()
def set_clip_markers(ctx: Context, track_index: int, clip_index: int, start_marker: float = None,
                     end_marker: float = None, arrangement_clip_index: int = None) -> str:
    """Set clip start/end markers in beats (get_clip_info already reads them). Omit fields to leave unchanged.

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if start_marker is not None:
            params["start_marker"] = start_marker
        if end_marker is not None:
            params["end_marker"] = end_marker
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_markers", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip markers: {str(e)}")
        return f"Error setting clip markers: {str(e)}"

@mcp.tool()
def set_clip_signature(ctx: Context, track_index: int, clip_index: int, numerator: int,
                       denominator: int, arrangement_clip_index: int = None) -> str:
    """Set a clip's time signature (numerator/denominator, e.g. 4/4).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index,
                  "numerator": numerator, "denominator": denominator}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_signature", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip signature: {str(e)}")
        return f"Error setting clip signature: {str(e)}"

@mcp.tool()
def quantize_pitch(ctx: Context, track_index: int, clip_index: int, pitch: int, grid: int = 5,
                   strength: float = 1.0, arrangement_clip_index: int = None) -> str:
    """Quantize one MIDI pitch in a clip. Same grid enum as quantize_clip.

    Parameters:
    - pitch: MIDI note 0-127
    - grid: 1=1/4, 2=1/8, 3=1/8+1/8T, 4=1/8T, 5=1/16 (default), 6=1/16+1/16T, 7=1/16T, 8=1/32
    - strength: 0.0-1.0 (1.0 = snap fully)
    - arrangement_clip_index: optional arrangement clip, same as add_notes_to_clip
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "pitch": pitch,
                  "grid": grid, "strength": strength}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("quantize_pitch", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error quantizing pitch: {str(e)}")
        return f"Error quantizing pitch: {str(e)}"

@mcp.tool()
def set_clip_ram_mode(ctx: Context, track_index: int, clip_index: int, ram_mode: bool,
                      arrangement_clip_index: int = None) -> str:
    """Enable or disable RAM mode on an audio clip (clip.ram_mode).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "ram_mode": ram_mode}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("set_clip_ram_mode", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting clip RAM mode: {str(e)}")
        return f"Error setting clip RAM mode: {str(e)}"

@mcp.tool()
def convert_clip_time(ctx: Context, track_index: int, clip_index: int, beat_time: float = None,
                      sample_time: float = None, arrangement_clip_index: int = None) -> str:
    """Convert between beat time and sample time on an audio clip (read-only).

    Provide beat_time (beats) or sample_time (seconds). Session slot, or an arrangement
    clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if beat_time is not None:
            params["beat_time"] = beat_time
        if sample_time is not None:
            params["sample_time"] = sample_time
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("convert_clip_time", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error converting clip time: {str(e)}")
        return f"Error converting clip time: {str(e)}"

