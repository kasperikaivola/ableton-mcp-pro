import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def get_session_info(ctx: Context) -> str:
    """Get detailed information about the current Ableton session"""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_session_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting session info from Ableton: {str(e)}")
        return f"Error getting session info: {str(e)}"

@mcp.tool()
def get_application_info(ctx: Context) -> str:
    """Read Live's version and current dialog state via the Remote Script backend.

    Dialog fields are returned when supported by the installed Live version.
    """
    try:
        result = get_ableton_connection().send_command("get_application_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting application info: {str(e)}")
        return f"Error getting application info: {str(e)}"

@mcp.tool()
def press_current_dialog_button(ctx: Context, index: int) -> str:
    """Press a zero-based button in Live's current dialog via the Remote Script backend.

    The backend validates the index and reports an error for an unavailable dialog or button.
    """
    try:
        result = get_ableton_connection().send_command("press_current_dialog_button", {
            "index": index
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error pressing current dialog button: {str(e)}")
        return f"Error pressing current dialog button: {str(e)}"

@mcp.tool()
def set_tempo(ctx: Context, tempo: float) -> str:
    """
    Set the tempo of the Ableton session.
    
    Parameters:
    - tempo: The new tempo in BPM
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_tempo", {"tempo": tempo})
        return f"Set tempo to {tempo} BPM"
    except Exception as e:
        logger.error(f"Error setting tempo: {str(e)}")
        return f"Error setting tempo: {str(e)}"

@mcp.tool()
def play_arrangement(ctx: Context, time: float = 0.0) -> str:
    """Play the arrangement from a specific position. Stops all session clips and switches to arrangement view.

    Parameters:
    - time: Position in beats to start from (0.0 = start). Default 0.0.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("play_arrangement", {"time": time})
        return f"Playing arrangement from beat {time}"
    except Exception as e:
        logger.error(f"Error playing arrangement: {str(e)}")
        return f"Error playing arrangement: {str(e)}"

@mcp.tool()
def capture_midi(ctx: Context, destination: int = 0) -> str:
    """Capture recently played MIDI into a new clip.

    Parameters:
    - destination: Capture destination: 0 = auto (Ableton chooses based on the
                   playback context), 1 = session, or 2 = arrangement.
    """
    if isinstance(destination, bool) or not isinstance(destination, int) or destination not in (0, 1, 2):
        return "Error capturing MIDI: destination must be 0 (auto), 1 (session), or 2 (arrangement)"
    try:
        result = get_ableton_connection().send_command("capture_midi", {
            "destination": destination
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error capturing MIDI: {str(e)}")
        return f"Error capturing MIDI: {str(e)}"

@mcp.tool()
def start_playback(ctx: Context) -> str:
    """Start playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("start_playback")
        return "Started playback"
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return f"Error starting playback: {str(e)}"

@mcp.tool()
def stop_playback(ctx: Context) -> str:
    """Stop playing the Ableton session."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("stop_playback")
        return "Stopped playback"
    except Exception as e:
        logger.error(f"Error stopping playback: {str(e)}")
        return f"Error stopping playback: {str(e)}"

@mcp.tool()
def set_song_time(ctx: Context, time: float) -> str:
    """
    Set the current song time (arrangement playback position) in beats.

    Parameters:
    - time: Position in beats (0.0 = start, 4.0 = bar 2, etc.)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_song_time", {
            "time": time
        })
        return f"Set song time to {result.get('current_song_time', time):.1f} beats"
    except Exception as e:
        logger.error(f"Error setting song time: {str(e)}")
        return f"Error setting song time: {str(e)}"

@mcp.tool()
def set_record_mode(ctx: Context, on: bool) -> str:
    """
    Enable or disable arrangement recording.
    When enabled, session clip playback is recorded into the arrangement.

    Parameters:
    - on: True to start recording, False to stop
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_record_mode", {
            "on": on
        })
        state = "enabled" if on else "disabled"
        return f"Arrangement recording {state}"
    except Exception as e:
        logger.error(f"Error setting record mode: {str(e)}")
        return f"Error setting record mode: {str(e)}"

@mcp.tool()
def set_arrangement_overdub(ctx: Context, on: bool) -> str:
    """
    Enable or disable arrangement overdub.
    When enabled, new recordings are layered on top of existing arrangement clips.

    Parameters:
    - on: True to enable overdub, False to disable
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_arrangement_overdub", {
            "on": on
        })
        state = "enabled" if result.get("arrangement_overdub") else "disabled"
        return f"Arrangement overdub {state}"
    except Exception as e:
        logger.error(f"Error setting arrangement overdub: {str(e)}")
        return f"Error setting arrangement overdub: {str(e)}"

@mcp.tool()
def set_back_to_arranger(ctx: Context, value: bool = False) -> str:
    """Return playback to the arrangement (what the Back to Arrangement button does).

    Live's flag is True while session clips override the arrangement; this sets it to `value`
    (default False = arrangement plays; True = session takes over). Note: with record mode on,
    an overridden arrangement gets recorded over with whatever the session plays, including silence.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_back_to_arranger", {"value": value})
        return "Returned to arrangement"
    except Exception as e:
        logger.error(f"Error setting back to arranger: {str(e)}")
        return f"Error setting back to arranger: {str(e)}"

@mcp.tool()
def set_arrangement_loop(ctx: Context, on: bool, start: float = 0.0, length: float = 16.0) -> str:
    """
    Set arrangement loop on/off, start position and length.

    Parameters:
    - on: True to enable loop, False to disable
    - start: Loop start position in beats
    - length: Loop length in beats (e.g. 16.0 = 4 bars)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_arrangement_loop", {
            "on": on,
            "start": start,
            "length": length
        })
        if on:
            return f"Loop enabled: start={result.get('loop_start', start):.1f}, length={result.get('loop_length', length):.1f} beats"
        else:
            return "Loop disabled"
    except Exception as e:
        logger.error(f"Error setting arrangement loop: {str(e)}")
        return f"Error setting arrangement loop: {str(e)}"

@mcp.tool()
def set_time_signature(ctx: Context, numerator: int, denominator: int) -> str:
    """
    Set the song time signature.

    Parameters:
    - numerator: Time signature numerator (e.g., 4 for 4/4)
    - denominator: Time signature denominator (e.g., 4 for 4/4)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_time_signature", {
            "numerator": numerator,
            "denominator": denominator
        })
        return f"Set time signature to {result.get('numerator', numerator)}/{result.get('denominator', denominator)}"
    except Exception as e:
        logger.error(f"Error setting time signature: {str(e)}")
        return f"Error setting time signature: {str(e)}"

@mcp.tool()
def set_metronome(ctx: Context, on: bool) -> str:
    """
    Enable or disable the metronome.

    Parameters:
    - on: True to enable, False to disable
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_metronome", {"on": on})
        state = "enabled" if result.get("metronome") else "disabled"
        return f"Metronome {state}"
    except Exception as e:
        logger.error(f"Error setting metronome: {str(e)}")
        return f"Error setting metronome: {str(e)}"

@mcp.tool()
def undo(ctx: Context) -> str:
    """Undo the last action in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("undo", {})
        return "Undone"
    except Exception as e:
        logger.error(f"Error undoing: {str(e)}")
        return f"Error undoing: {str(e)}"

@mcp.tool()
def redo(ctx: Context) -> str:
    """Redo the last undone action in Ableton."""
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("redo", {})
        return "Redone"
    except Exception as e:
        logger.error(f"Error redoing: {str(e)}")
        return f"Error redoing: {str(e)}"

# ---- clip editing, device bypass, return tracks, drum pads ----
# Clip tools take a session slot (clip_index) or, with arrangement_clip_index set, an arrangement clip
# (index as listed by get_arrangement_clips). Audio clips can only be created in the arrangement.

@mcp.tool()
def stop_all_clips(ctx: Context, quantized: bool = True) -> str:
    """Stop every playing session clip (quantized = at the next launch-quantization point)."""
    try:
        get_ableton_connection().send_command("stop_all_clips", {"quantized": quantized})
        return "Stopped all clips"
    except Exception as e:
        logger.error(f"Error stopping all clips: {str(e)}")
        return f"Error stopping all clips: {str(e)}"

@mcp.tool()
def get_cue_points(ctx: Context) -> str:
    """List arrangement cue points (name, time in beats). Use jump_to_cue / toggle_cue to navigate or set them."""
    try:
        result = get_ableton_connection().send_command("get_cue_points")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cue points: {str(e)}")
        return f"Error getting cue points: {str(e)}"

@mcp.tool()
def toggle_cue(ctx: Context) -> str:
    """Set or delete a cue point at the current arrangement song time (song.set_or_delete_cue)."""
    try:
        result = get_ableton_connection().send_command("toggle_cue")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error toggling cue: {str(e)}")
        return f"Error toggling cue: {str(e)}"

@mcp.tool()
def jump_to_cue(ctx: Context, direction: str = None, index: int = None) -> str:
    """Jump the playhead to a cue point.

    Parameters:
    - direction: 'next' or 'prev' (song.jump_to_next_cue / jump_to_prev_cue).
      Returns the destination cue time, not a possibly stale current_song_time.
    - index: jump to this cue from get_cue_points instead of next/prev
    """
    try:
        params = {}
        if direction is not None:
            params["direction"] = direction
        if index is not None:
            params["index"] = index
        result = get_ableton_connection().send_command("jump_to_cue", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping to cue: {str(e)}")
        return f"Error jumping to cue: {str(e)}"

@mcp.tool()
def tap_tempo(ctx: Context) -> str:
    """Tap the song tempo once (song.tap_tempo)."""
    try:
        result = get_ableton_connection().send_command("tap_tempo")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error tapping tempo: {str(e)}")
        return f"Error tapping tempo: {str(e)}"

@mcp.tool()
def jump_by(ctx: Context, beats: float) -> str:
    """Jump the playhead by a number of beats (song.jump_by). Negative values jump backward."""
    try:
        result = get_ableton_connection().send_command("jump_by", {"beats": beats})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error jumping by beats: {str(e)}")
        return f"Error jumping by beats: {str(e)}"

@mcp.tool()
def continue_playing(ctx: Context) -> str:
    """Continue playback from the current position (song.continue_playing)."""
    try:
        result = get_ableton_connection().send_command("continue_playing")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error continuing playback: {str(e)}")
        return f"Error continuing playback: {str(e)}"

@mcp.tool()
def set_session_record(ctx: Context, on: bool) -> str:
    """Enable or disable session recording (song.session_record)."""
    try:
        result = get_ableton_connection().send_command("set_session_record", {"on": on})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting session record: {str(e)}")
        return f"Error setting session record: {str(e)}"

@mcp.tool()
def set_session_automation_record(ctx: Context, on: bool) -> str:
    """Enable or disable session automation recording (song.session_automation_record)."""
    try:
        result = get_ableton_connection().send_command("set_session_automation_record", {"on": on})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting session automation record: {str(e)}")
        return f"Error setting session automation record: {str(e)}"

@mcp.tool()
def re_enable_automation(ctx: Context) -> str:
    """Re-enable automation that was overridden by a manual tweak (song.re_enable_automation)."""
    try:
        result = get_ableton_connection().send_command("re_enable_automation")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error re-enabling automation: {str(e)}")
        return f"Error re-enabling automation: {str(e)}"

@mcp.tool()
def set_count_in_duration(ctx: Context, bars: int) -> str:
    """Set count-in duration in bars (song.count_in_duration; typically 0, 1, 2, or 4)."""
    try:
        result = get_ableton_connection().send_command("set_count_in_duration", {"bars": bars})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting count-in duration: {str(e)}")
        return f"Error setting count-in duration: {str(e)}"

@mcp.tool()
def set_exclusive_arm(ctx: Context, on: bool) -> str:
    """Enable or disable exclusive arm (arming one track disarms others)."""
    try:
        result = get_ableton_connection().send_command("set_exclusive_arm", {"on": on})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting exclusive arm: {str(e)}")
        return f"Error setting exclusive arm: {str(e)}"

@mcp.tool()
def set_punch(ctx: Context, punch_in: bool = None, punch_out: bool = None) -> str:
    """Set arrangement punch-in and/or punch-out. Omit a field to leave it unchanged."""
    try:
        params = {}
        if punch_in is not None:
            params["punch_in"] = punch_in
        if punch_out is not None:
            params["punch_out"] = punch_out
        result = get_ableton_connection().send_command("set_punch", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting punch: {str(e)}")
        return f"Error setting punch: {str(e)}"

@mcp.tool()
def set_song_scale(ctx: Context, scale_name: str = None, root_note: int = None) -> str:
    """Set the song scale name and/or root note (MIDI pitch class 0-11, C=0). Omit a field to leave unchanged."""
    try:
        params = {}
        if scale_name is not None:
            params["scale_name"] = scale_name
        if root_note is not None:
            params["root_note"] = root_note
        result = get_ableton_connection().send_command("set_song_scale", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting song scale: {str(e)}")
        return f"Error setting song scale: {str(e)}"

@mcp.tool()
def set_crossfader(ctx: Context, value: float) -> str:
    """Set the master crossfader position, 0.0 (A) through 1.0 (B)."""
    try:
        result = get_ableton_connection().send_command("set_crossfader", {"value": value})
        return f"Crossfader {result.get('value', value)}"
    except Exception as e:
        logger.error(f"Error setting crossfader: {str(e)}")
        return f"Error setting crossfader: {str(e)}"

@mcp.tool()
def set_cue_volume(ctx: Context, value: float) -> str:
    """Set cue/preview volume, normalized 0.0-1.0 (master mixer cue_volume)."""
    try:
        result = get_ableton_connection().send_command("set_cue_volume", {"value": value})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting cue volume: {str(e)}")
        return f"Error setting cue volume: {str(e)}"

@mcp.tool()
def set_crossfade_assign(ctx: Context, track_index: int, assign: int) -> str:
    """Assign a track to the crossfader: 0=A, 1=none, 2=B."""
    try:
        result = get_ableton_connection().send_command("set_crossfade_assign", {
            "track_index": track_index, "assign": assign})
        labels = {0: "A", 1: "none", 2: "B"}
        return f"Track {track_index} crossfade {labels.get(result.get('assign', assign), assign)}"
    except Exception as e:
        logger.error(f"Error setting crossfade assign: {str(e)}")
        return f"Error setting crossfade assign: {str(e)}"

@mcp.tool()
def show_view(ctx: Context, view_name: str) -> str:
    """Show an Ableton view by name (app.view.show_view).

    Common names: 'Session', 'Arranger', 'Browser', 'Detail/Clip', 'Detail/DeviceChain'.
    """
    try:
        get_ableton_connection().send_command("show_view", {"view_name": view_name})
        return f"Showed view '{view_name}'"
    except Exception as e:
        logger.error(f"Error showing view: {str(e)}")
        return f"Error showing view: {str(e)}"

