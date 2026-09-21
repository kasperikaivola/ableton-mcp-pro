import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp

@mcp.tool()
def set_track_volume(ctx: Context, track_index: int, volume: float) -> str:
    """
    Set a track's volume level using a normalized value (0.0 to 1.0).
    Use track_index -1 for the master track.

    Parameters:
    - track_index: The index of the track (-1 for master)
    - volume: Normalized volume value (0.0 = silent, 0.85 = default, 1.0 = max)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_volume", {
            "track_index": track_index,
            "volume": volume
        })
        track_name = result.get("track_name", "unknown")
        return f"Set '{track_name}' volume to {volume:.2f}"
    except Exception as e:
        logger.error(f"Error setting track volume: {str(e)}")
        return f"Error setting track volume: {str(e)}"

@mcp.tool()
def set_track_panning(ctx: Context, track_index: int, panning: float) -> str:
    """
    Set a track's panning using a normalized value (0.0 to 1.0, where 0.5 is center).
    Use track_index -1 for the master track.

    Parameters:
    - track_index: The index of the track (-1 for master)
    - panning: Normalized panning value (0.0 = full left, 0.5 = center, 1.0 = full right)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_panning", {
            "track_index": track_index,
            "panning": panning
        })
        track_name = result.get("track_name", "unknown")
        return f"Set '{track_name}' panning to {panning:.2f}"
    except Exception as e:
        logger.error(f"Error setting track panning: {str(e)}")
        return f"Error setting track panning: {str(e)}"

@mcp.tool()
def set_track_color(ctx: Context, track_index: int, color_index: int = None, color: int = None) -> str:
    """Set a track's color. Provide color_index (Live palette) and/or color (RGB int).

    track_index -1 = master, -2/-3 = returns.
    """
    try:
        params = {"track_index": track_index}
        if color_index is not None:
            params["color_index"] = color_index
        if color is not None:
            params["color"] = color
        result = get_ableton_connection().send_command("set_track_color", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting track color: {str(e)}")
        return f"Error setting track color: {str(e)}"

@mcp.tool()
def set_track_arm(ctx: Context, track_index: int, arm: bool) -> str:
    """
    Arm or disarm a track for recording.

    Parameters:
    - track_index: The index of the track
    - arm: True to arm, False to disarm
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_arm", {
            "track_index": track_index,
            "arm": arm
        })
        state = "armed" if result.get("arm") else "disarmed"
        return f"Track '{result.get('track_name', '')}' {state}"
    except Exception as e:
        logger.error(f"Error setting track arm: {str(e)}")
        return f"Error setting track arm: {str(e)}"

@mcp.tool()
def set_send_level(ctx: Context, track_index: int, send_index: int, value: float) -> str:
    """
    Set the send level for a track.

    Parameters:
    - track_index: The index of the track (use -1 for master, -2/-3 for returns)
    - send_index: The index of the send (0 = Send A, 1 = Send B, etc.)
    - value: Normalized value 0.0-1.0
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_send_level", {
            "track_index": track_index,
            "send_index": send_index,
            "value": value
        })
        return f"Set send {send_index} on track {track_index} to {value}"
    except Exception as e:
        logger.error(f"Error setting send level: {str(e)}")
        return f"Error setting send level: {str(e)}"

@mcp.tool()
def set_track_monitoring(ctx: Context, track_index: int, state: int) -> str:
    """Set track monitoring state.

    Parameters:
    - track_index: The index of the track
    - state: 0=In, 1=Auto, 2=Off
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_monitoring", {"track_index": track_index, "state": state})
        states = {0: "In", 1: "Auto", 2: "Off"}
        return f"Set monitoring to {states.get(state, str(state))}"
    except Exception as e:
        logger.error(f"Error setting monitoring: {str(e)}")
        return f"Error setting monitoring: {str(e)}"

@mcp.tool()
def get_track_routing(ctx: Context, track_index: int) -> str:
    """Get input/output routing information for a track.

    Parameters:
    - track_index: The index of the track (0+ for regular, -1 for master, -2/-3 for returns)
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_track_routing", {"track_index": track_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting routing: {str(e)}")
        return f"Error getting routing: {str(e)}"

@mcp.tool()
def set_track_input_routing(ctx: Context, track_index: int, routing_type_name: str, channel_name: str = None) -> str:
    """Set the input routing of a track by name.

    Parameters:
    - track_index: The index of the track
    - routing_type_name: Name of the routing type (use get_track_routing to see available options)
    - channel_name: Optional channel within it ("Ch. 5", "1/2", "Post FX"); default: the first
    """
    try:
        ableton = get_ableton_connection()
        params = {"track_index": track_index, "routing_type_name": routing_type_name}
        if channel_name: params["channel_name"] = channel_name
        result = ableton.send_command("set_track_input_routing", params)
        return f"Set input routing to '{routing_type_name}' / {result.get('input_routing_channel')}"
    except Exception as e:
        logger.error(f"Error setting input routing: {str(e)}")
        return f"Error setting input routing: {str(e)}"

@mcp.tool()
def set_track_output_routing(ctx: Context, track_index: int, routing_type_name: str) -> str:
    """Set the output routing of a track by name.

    Parameters:
    - track_index: The index of the track
    - routing_type_name: Name of the routing type (use get_track_routing to see available options)
    - channel_name: Optional channel within it ("Ch. 5", "1/2", "Post FX"); default: the first
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("set_track_output_routing", {"track_index": track_index, "routing_type_name": routing_type_name})
        return f"Set output routing to '{routing_type_name}'"
    except Exception as e:
        logger.error(f"Error setting output routing: {str(e)}")
        return f"Error setting output routing: {str(e)}"

# ---- groove, racks, sidechain, cues, views, warp markers ----

@mcp.tool()
def get_groove_pool(ctx: Context) -> str:
    """List grooves in the song Groove Pool (index, name). Pass the index to apply_groove."""
    try:
        result = get_ableton_connection().send_command("get_groove_pool")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting groove pool: {str(e)}")
        return f"Error getting groove pool: {str(e)}"

@mcp.tool()
def set_groove_amount(ctx: Context, amount: float) -> str:
    """Set the song's global groove amount, typically 0.0-1.0. Clips still need a groove from apply_groove."""
    try:
        result = get_ableton_connection().send_command("set_groove_amount", {"amount": amount})
        return f"Groove amount {result.get('amount', amount)}"
    except Exception as e:
        logger.error(f"Error setting groove amount: {str(e)}")
        return f"Error setting groove amount: {str(e)}"

@mcp.tool()
def apply_groove(ctx: Context, track_index: int, clip_index: int, groove_index: int, arrangement_clip_index: int = None) -> str:
    """Assign a Groove Pool groove to a clip. groove_index comes from get_groove_pool.

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index, "groove_index": groove_index}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        result = get_ableton_connection().send_command("apply_groove", params)
        return f"Applied groove {result.get('groove_index', groove_index)} ({result.get('groove_name', '')})"
    except Exception as e:
        logger.error(f"Error applying groove: {str(e)}")
        return f"Error applying groove: {str(e)}"

@mcp.tool()
def clear_clip_groove(ctx: Context, track_index: int, clip_index: int, arrangement_clip_index: int = None) -> str:
    """Remove the assigned groove from a clip.

    Session slot, or an arrangement clip via arrangement_clip_index like add_notes_to_clip.
    """
    try:
        params = {"track_index": track_index, "clip_index": clip_index}
        if arrangement_clip_index is not None:
            params["arrangement_clip_index"] = arrangement_clip_index
        get_ableton_connection().send_command("clear_clip_groove", params)
        return f"Cleared groove on track {track_index}, clip {clip_index}"
    except Exception as e:
        logger.error(f"Error clearing clip groove: {str(e)}")
        return f"Error clearing clip groove: {str(e)}"

