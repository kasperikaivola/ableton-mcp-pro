import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def get_rack_chains(ctx: Context, track_index: int, device_index: int) -> str:
    """List chains inside an Instrument/Audio/MIDI/Drum Rack: names, mixer, nested devices.

    Creating macro maps is GUI-only. Use insert_rack_chain (Live 12.3+) to add chains.
    """
    try:
        result = get_ableton_connection().send_command("get_rack_chains", {
            "track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting rack chains: {str(e)}")
        return f"Error getting rack chains: {str(e)}"

@mcp.tool()
def get_rack_macros(ctx: Context, track_index: int, device_index: int) -> str:
    """Read rack macro state, including visible_macro_count, variation_count,
    selected_variation_index, and mapped macros. Mapping new parameters remains
    GUI-only; use set_device_parameter to change an existing mapped macro.
    """
    try:
        result = get_ableton_connection().send_command("get_rack_macros", {
            "track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting rack macros: {str(e)}")
        return f"Error getting rack macros: {str(e)}"

@mcp.tool()
def add_macro(ctx: Context, track_index: int, device_index: int) -> str:
    """Add one macro to a RackDevice using the Live Remote Script backend."""
    try:
        result = get_ableton_connection().send_command("add_macro", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error adding rack macro: {str(e)}")
        return f"Error adding rack macro: {str(e)}"

@mcp.tool()
def remove_macro(ctx: Context, track_index: int, device_index: int) -> str:
    """Remove one macro from a RackDevice using the Live Remote Script backend."""
    try:
        result = get_ableton_connection().send_command("remove_macro", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error removing rack macro: {str(e)}")
        return f"Error removing rack macro: {str(e)}"

@mcp.tool()
def randomize_macros(ctx: Context, track_index: int, device_index: int) -> str:
    """Randomize a RackDevice's macro values via the Live Remote Script backend."""
    try:
        result = get_ableton_connection().send_command("randomize_macros", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error randomizing rack macros: {str(e)}")
        return f"Error randomizing rack macros: {str(e)}"

@mcp.tool()
def store_macro_variation(ctx: Context, track_index: int, device_index: int) -> str:
    """Store the current RackDevice macro values as a variation."""
    try:
        result = get_ableton_connection().send_command("store_macro_variation", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error storing rack macro variation: {str(e)}")
        return f"Error storing rack macro variation: {str(e)}"

@mcp.tool()
def recall_macro_variation(
    ctx: Context,
    track_index: int,
    device_index: int,
    variation_index: int,
) -> str:
    """Recall a RackDevice macro variation by its zero-based variation index."""
    try:
        result = get_ableton_connection().send_command("recall_macro_variation", {
            "track_index": track_index,
            "device_index": device_index,
            "variation_index": variation_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error recalling rack macro variation: {str(e)}")
        return f"Error recalling rack macro variation: {str(e)}"

@mcp.tool()
def delete_macro_variation(
    ctx: Context,
    track_index: int,
    device_index: int,
    variation_index: int,
) -> str:
    """Delete a RackDevice macro variation by its zero-based variation index."""
    try:
        result = get_ableton_connection().send_command("delete_macro_variation", {
            "track_index": track_index,
            "device_index": device_index,
            "variation_index": variation_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error deleting rack macro variation: {str(e)}")
        return f"Error deleting rack macro variation: {str(e)}"

@mcp.tool()
def insert_rack_chain(ctx: Context, track_index: int, device_index: int, index: int = -1, name: str = None) -> str:
    """Insert a chain into an Instrument/Audio/MIDI Rack. Live 12.3+ only (RackDevice.create_chain).

    index -1 appends. Creating macro maps is GUI-only.
    """
    try:
        params = {"track_index": track_index, "device_index": device_index, "index": index}
        if name is not None:
            params["name"] = name
        result = get_ableton_connection().send_command("insert_rack_chain", params)
        return f"Inserted chain {result.get('chain_index', index)} '{result.get('name', name or '')}'"
    except Exception as e:
        logger.error(f"Error inserting rack chain: {str(e)}")
        return f"Error inserting rack chain: {str(e)}"

@mcp.tool()
def set_chain_mixer(ctx: Context, track_index: int, device_index: int, chain_index: int,
                    mute: bool = None, solo: bool = None, volume: float = None, panning: float = None) -> str:
    """Set mixer properties on a rack chain. Omit fields you do not want to change.

    Parameters:
    - mute, solo: chain mute/solo
    - volume: 0.0-1.0
    - panning: 0.0-1.0 (left-right). Negative values in -1..1 are also accepted and converted.
    """
    try:
        params = {"track_index": track_index, "device_index": device_index, "chain_index": chain_index}
        if mute is not None:
            params["mute"] = mute
        if solo is not None:
            params["solo"] = solo
        if volume is not None:
            params["volume"] = volume
        if panning is not None:
            params["panning"] = panning
        result = get_ableton_connection().send_command("set_chain_mixer", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting chain mixer: {str(e)}")
        return f"Error setting chain mixer: {str(e)}"

@mcp.tool()
def get_warp_markers(ctx: Context, track_index: int, clip_index: int, arrangement_clip_index: int = None) -> str:
    """List warp markers on an audio clip (beat_time / sample_time).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("get_warp_markers", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting warp markers: {str(e)}")
        return f"Error getting warp markers: {str(e)}"

@mcp.tool()
def add_warp_marker(ctx: Context, track_index: int, clip_index: int, beat_time: float,
                    sample_time: float = None, arrangement_clip_index: int = None) -> str:
    """Add a warp marker on an audio clip. The Remote Script constructs a WarpMarker
    from beat_time (beats) and optional sample_time (seconds into the sample).

    Omit sample_time to keep the current warp mapping at that beat. Session slot, or
    an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "beat_time": beat_time}
        if sample_time is not None:
            params["sample_time"] = sample_time
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("add_warp_marker", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error adding warp marker: {str(e)}")
        return f"Error adding warp marker: {str(e)}"

@mcp.tool()
def move_warp_marker(ctx: Context, track_index: int, clip_index: int, beat_time: float,
                     beat_time_distance: float, arrangement_clip_index: int = None) -> str:
    """Move a warp marker at beat_time by beat_time_distance (beats).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index,
                  "beat_time": beat_time, "beat_time_distance": beat_time_distance}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("move_warp_marker", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error moving warp marker: {str(e)}")
        return f"Error moving warp marker: {str(e)}"

@mcp.tool()
def delete_warp_marker(ctx: Context, track_index: int, clip_index: int, beat_time: float,
                       arrangement_clip_index: int = None) -> str:
    """Delete the warp marker at beat_time (beats).

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "beat_time": beat_time}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("delete_warp_marker", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error deleting warp marker: {str(e)}")
        return f"Error deleting warp marker: {str(e)}"

