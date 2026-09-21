import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def get_track_info(ctx: Context, track_index: int) -> str:
    """
    Get detailed information about a specific track in Ableton.
    
    Parameters:
    - track_index: 0+ for regular tracks; -1 for the master track; -2 for
                   Return A, -3 for Return B, and so on for additional returns.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_info", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting track info from Ableton: {str(e)}")
        return f"Error getting track info: {str(e)}"

@mcp.tool()
def create_midi_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new MIDI track in the Ableton session.
    
    Parameters:
    - index: The index to insert the track at (-1 = end of list)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_midi_track", {"index": index})
        return f"Created new MIDI track: {result.get('name', 'unknown')}"
    except Exception as e:
        logger.error(f"Error creating MIDI track: {str(e)}")
        return f"Error creating MIDI track: {str(e)}"

@mcp.tool()
def set_track_name(ctx: Context, track_index: int, name: str) -> str:
    """
    Set the name of a track.
    
    Parameters:
    - track_index: The index of the track to rename
    - name: The new name for the track
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_name", {"track_index": track_index, "name": name})
        return f"Renamed track to: {result.get('name', name)}"
    except Exception as e:
        logger.error(f"Error setting track name: {str(e)}")
        return f"Error setting track name: {str(e)}"

@mcp.tool()
def fire_scene(ctx: Context, scene_index: int) -> str:
    """
    Fire (launch) all clips in a scene at once.

    Parameters:
    - scene_index: The index of the scene to fire
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("fire_scene", {
            "scene_index": scene_index
        })
        scene_name = result.get("scene_name", "")
        return f"Fired scene {scene_index}" + (f" ({scene_name})" if scene_name else "")
    except Exception as e:
        logger.error(f"Error firing scene: {str(e)}")
        return f"Error firing scene: {str(e)}"

@mcp.tool()
def set_track_mute(ctx: Context, track_index: int, mute: bool) -> str:
    """
    Mute or unmute a track.

    Parameters:
    - track_index: The index of the track (-1 for master)
    - mute: True to mute, False to unmute
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_mute", {
            "track_index": track_index,
            "mute": mute
        })
        track_name = result.get("track_name", "unknown")
        state = "muted" if mute else "unmuted"
        return f"Track '{track_name}' {state}"
    except Exception as e:
        logger.error(f"Error setting track mute: {str(e)}")
        return f"Error setting track mute: {str(e)}"

@mcp.tool()
def set_track_solo(ctx: Context, track_index: int, solo: bool) -> str:
    """
    Solo or unsolo a track.

    Parameters:
    - track_index: The index of the track
    - solo: True to solo, False to unsolo
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_solo", {
            "track_index": track_index,
            "solo": solo
        })
        track_name = result.get("track_name", "unknown")
        state = "soloed" if solo else "unsoloed"
        return f"Track '{track_name}' {state}"
    except Exception as e:
        logger.error(f"Error setting track solo: {str(e)}")
        return f"Error setting track solo: {str(e)}"

@mcp.tool()
def create_scene(ctx: Context, index: int = -1) -> str:
    """
    Create a new scene at the specified index.

    Parameters:
    - index: Position to insert the scene (-1 to add at the end)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_scene", {
            "index": index
        })
        return f"Created scene at index {result.get('scene_index', index)} (total: {result.get('scene_count', '?')} scenes)"
    except Exception as e:
        logger.error(f"Error creating scene: {str(e)}")
        return f"Error creating scene: {str(e)}"

@mcp.tool()
def set_scene_name(ctx: Context, scene_index: int, name: str) -> str:
    """
    Set a scene's name (e.g. "Intro", "Drop", "Outro").

    Parameters:
    - scene_index: The index of the scene
    - name: The name to set
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_scene_name", {
            "scene_index": scene_index,
            "name": name
        })
        return f"Set scene {scene_index} name to '{result.get('name', name)}'"
    except Exception as e:
        logger.error(f"Error setting scene name: {str(e)}")
        return f"Error setting scene name: {str(e)}"

@mcp.tool()
def set_scene_color(ctx: Context, scene_index: int, color_index: int = None, color: int = None) -> str:
    """Set a scene's color. Provide color_index (Live palette) and/or color (RGB int)."""
    try:
        params = {"scene_index": scene_index}
        if color_index is not None:
            params["color_index"] = color_index
        if color is not None:
            params["color"] = color
        result = get_ableton_connection().send_command("set_scene_color", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene color: {str(e)}")
        return f"Error setting scene color: {str(e)}"

@mcp.tool()
def duplicate_scene(ctx: Context, index: int) -> str:
    """Duplicate a scene at the given index (song.duplicate_scene)."""
    try:
        result = get_ableton_connection().send_command("duplicate_scene", {"index": index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error duplicating scene: {str(e)}")
        return f"Error duplicating scene: {str(e)}"

@mcp.tool()
def set_scene_tempo(ctx: Context, scene_index: int, tempo: float) -> str:
    """Set a scene's tempo in BPM. 0 typically means follow the song tempo."""
    try:
        result = get_ableton_connection().send_command("set_scene_tempo", {
            "scene_index": scene_index, "tempo": tempo})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene tempo: {str(e)}")
        return f"Error setting scene tempo: {str(e)}"

@mcp.tool()
def set_scene_signature(ctx: Context, scene_index: int, numerator: int, denominator: int) -> str:
    """Set a scene's time signature (numerator/denominator, e.g. 4/4)."""
    try:
        result = get_ableton_connection().send_command("set_scene_signature", {
            "scene_index": scene_index, "numerator": numerator, "denominator": denominator})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting scene signature: {str(e)}")
        return f"Error setting scene signature: {str(e)}"

@mcp.tool()
def create_audio_track(ctx: Context, index: int = -1) -> str:
    """
    Create a new audio track at the specified index.

    Parameters:
    - index: Position to insert the track (-1 to add at the end)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("create_audio_track", {
            "index": index
        })
        return f"Created audio track '{result.get('name', '')}' at index {result.get('index', index)}"
    except Exception as e:
        logger.error(f"Error creating audio track: {str(e)}")
        return f"Error creating audio track: {str(e)}"

@mcp.tool()
def delete_track(ctx: Context, track_index: int) -> str:
    """
    Delete a track.

    Parameters:
    - track_index: The index of the track to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_track", {
            "track_index": track_index
        })
        return f"Deleted track '{result.get('deleted_track', '')}' (remaining: {result.get('track_count', '?')} tracks)"
    except Exception as e:
        logger.error(f"Error deleting track: {str(e)}")
        return f"Error deleting track: {str(e)}"

@mcp.tool()
def delete_scene(ctx: Context, scene_index: int) -> str:
    """
    Delete a scene.

    Parameters:
    - scene_index: The index of the scene to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_scene", {
            "scene_index": scene_index
        })
        return f"Deleted scene '{result.get('deleted_scene', '')}' (remaining: {result.get('scene_count', '?')} scenes)"
    except Exception as e:
        logger.error(f"Error deleting scene: {str(e)}")
        return f"Error deleting scene: {str(e)}"

@mcp.tool()
def duplicate_track(ctx: Context, track_index: int) -> str:
    """
    Duplicate a track (creates a copy with all clips and devices).

    Parameters:
    - track_index: The index of the track to duplicate
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("duplicate_track", {
            "track_index": track_index
        })
        return f"Duplicated '{result.get('original_track', '')}' → new track '{result.get('new_track_name', '')}' at index {result.get('new_track_index', '?')}"
    except Exception as e:
        logger.error(f"Error duplicating track: {str(e)}")
        return f"Error duplicating track: {str(e)}"

@mcp.tool()
def create_return_track(ctx: Context) -> str:
    """Create a new return track (appears as the next letter; address it as track_index -2, -3, ...)."""
    try:
        result = get_ableton_connection().send_command("create_return_track")
        return f"Created return track '{result.get('name', '')}'; {result.get('return_track_count')} returns now"
    except Exception as e:
        logger.error(f"Error creating return track: {str(e)}")
        return f"Error creating return track: {str(e)}"

@mcp.tool()
def delete_return_track(ctx: Context, index: int) -> str:
    """Delete a return track by position (0 = Return A, 1 = Return B, ...)."""
    try:
        result = get_ableton_connection().send_command("delete_return_track", {"index": index})
        return f"Deleted return track {index}; {result.get('return_track_count')} remain"
    except Exception as e:
        logger.error(f"Error deleting return track: {str(e)}")
        return f"Error deleting return track: {str(e)}"

@mcp.tool()
def capture_and_insert_scene(ctx: Context) -> str:
    """Capture currently playing session clips into a new scene (song.capture_and_insert_scene)."""
    try:
        result = get_ableton_connection().send_command("capture_and_insert_scene")
        return f"Captured scene '{result.get('name', '')}' at index {result.get('scene_index', '')}"
    except Exception as e:
        logger.error(f"Error capturing and inserting scene: {str(e)}")
        return f"Error capturing and inserting scene: {str(e)}"

