# ableton_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import os
import socket
import json
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AbletonMCPServer")

@dataclass
class AbletonConnection:
    host: str
    port: int
    sock: socket.socket = None
    
    def connect(self) -> bool:
        """Connect to the Ableton Remote Script socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Ableton at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ableton: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Ableton Remote Script"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Ableton: {str(e)}")
            finally:
                self.sock = None

    def receive_full_response(self, sock, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks.
        Uses whatever timeout is already set on the socket."""
        chunks = []
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    if not chunk:
                        if not chunks:
                            raise Exception("Connection closed before receiving any data")
                        break
                    
                    chunks.append(chunk)
                    
                    # Check if we've received a complete JSON object
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode('utf-8'))
                        logger.info(f"Received complete response ({len(data)} bytes)")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue
                except socket.timeout:
                    logger.warning("Socket timeout during chunked receive")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise
            
        # If we get here, we either timed out or broke out of the loop
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes)")
            try:
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received")
        else:
            raise Exception("No data received")

    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Ableton and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Ableton")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        # Check if this is a state-modifying command
        is_modifying_command = command_type in [
            "create_midi_track", "create_audio_track", "set_track_name",
            "create_clip", "create_audio_clip", "create_arrangement_audio_clip",
            "create_arrangement_midi_clip", "delete_arrangement_clip",
            "add_notes_to_clip", "apply_note_modifications", "set_clip_name",
            "set_tempo", "fire_clip", "stop_clip", "set_device_parameter",
            "batch_set_device_parameters", "set_plugin_preset",
            "start_playback", "stop_playback", "load_instrument_or_effect",
            "load_browser_item", "set_track_volume", "set_track_panning",
            "play_arrangement", "fire_scene", "set_song_time", "set_record_mode",
            "set_arrangement_overdub", "set_back_to_arranger",
            "set_arrangement_loop",
            "set_track_mute", "set_track_solo",
            "delete_clip", "duplicate_clip", "duplicate_clip_to_arrangement",
            "create_scene", "delete_scene", "set_scene_name",
            "delete_track", "record_arrangement",
            "delete_device", "duplicate_track", "set_clip_loop",
            "set_track_arm", "set_send_level", "set_time_signature",
            "set_track_monitoring",
            "set_track_input_routing", "set_track_output_routing", "set_metronome",
            "set_clip_envelope", "clear_clip_envelope",
            "undo", "redo", "capture_midi",
            "create_arrangement_audio_clips_batch", "remove_notes",
            "quantize_clip", "duplicate_clip_loop", "duplicate_region",
            "set_device_enabled", "create_return_track", "delete_return_track",
            "stop_all_clips", "set_clip_gain", "set_clip_pitch",
            "set_clip_warping", "set_clip_warp_mode", "resample_master",
            "move_device", "insert_device", "set_groove_amount", "apply_groove", "clear_clip_groove",
            "set_device_sidechain", "insert_rack_chain", "set_chain_mixer",
            "add_macro", "remove_macro", "randomize_macros",
            "store_macro_variation", "recall_macro_variation", "delete_macro_variation",
            "set_simpler_sample_window", "replace_simpler_sample",
            "capture_and_insert_scene", "crop_clip", "set_clip_launch",
            "toggle_cue", "jump_to_cue", "set_crossfader", "set_crossfade_assign",
            "show_view", "add_warp_marker",
            "set_clip_color", "set_clip_muted", "set_clip_markers",
            "set_clip_signature", "quantize_pitch", "set_clip_ram_mode",
            "move_warp_marker", "delete_warp_marker",
            "tap_tempo", "jump_by", "continue_playing",
            "set_session_record", "set_session_automation_record",
            "re_enable_automation", "set_count_in_duration",
            "set_exclusive_arm", "set_punch", "set_song_scale",
            "set_track_color", "set_scene_color", "duplicate_scene",
            "set_scene_tempo", "set_scene_signature", "set_cue_volume",
            "press_current_dialog_button"
        ]
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # For state-modifying commands, add a small delay to give Ableton time to process
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            # Set timeout based on command type
            if command_type == "record_arrangement":
                timeout = 600.0  # 10 minutes for arrangement recording
            elif command_type == "resample_master":
                timeout = 600.0  # 10 minutes for real-time master resampling
            elif is_modifying_command:
                timeout = 15.0
            else:
                timeout = 10.0
            self.sock.settimeout(timeout)
            
            # Receive the response
            response_data = self.receive_full_response(self.sock)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            # Parse the response
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"Ableton error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from Ableton"))
            
            # For state-modifying commands, add another small delay after receiving response
            if is_modifying_command:
                import time
                time.sleep(0.1)  # 100ms delay
            
            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from Ableton")
            self.sock = None
            raise Exception("Timeout waiting for Ableton response")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Connection to Ableton lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ableton: {str(e)}")
            if 'response_data' in locals() and response_data:
                logger.error(f"Raw response (first 200 bytes): {response_data[:200]}")
            self.sock = None
            raise Exception(f"Invalid response from Ableton: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with Ableton: {str(e)}")
            self.sock = None
            raise Exception(f"Communication error with Ableton: {str(e)}")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("AbletonMCP server starting up")
        
        try:
            ableton = get_ableton_connection()
            logger.info("Successfully connected to Ableton on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Ableton on startup: {str(e)}")
            logger.warning("Make sure the Ableton Remote Script is running")
        
        yield {}
    finally:
        global _ableton_connection
        if _ableton_connection:
            logger.info("Disconnecting from Ableton on shutdown")
            _ableton_connection.disconnect()
            _ableton_connection = None
        logger.info("AbletonMCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "AbletonMCP",
    # description="Ableton Live integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Global connection for resources
_ableton_connection = None

def get_ableton_connection():
    """Get or create a persistent Ableton connection"""
    global _ableton_connection
    
    if _ableton_connection is not None:
        try:
            # Test the connection with a simple ping
            # We'll try to send an empty message, which should fail if the connection is dead
            # but won't affect Ableton if it's alive
            _ableton_connection.sock.settimeout(1.0)
            _ableton_connection.sock.sendall(b'')
            return _ableton_connection
        except Exception as e:
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _ableton_connection.disconnect()
            except:
                pass
            _ableton_connection = None
    
    # Connection doesn't exist or is invalid, create a new one
    if _ableton_connection is None:
        # Try to connect up to 3 times with a short delay between attempts
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Connecting to Ableton (attempt {attempt}/{max_attempts})...")
                _ableton_connection = AbletonConnection(
                    host=os.environ.get("ABLETON_HOST", "localhost"),
                    # 9877 = Python Remote Script, 9878 = Max for Live device
                    port=int(os.environ.get("ABLETON_PORT", "9877")))
                if _ableton_connection.connect():
                    logger.info("Created new persistent connection to Ableton")
                    
                    # Validate connection with a simple command
                    try:
                        # Get session info as a test
                        _ableton_connection.send_command("get_session_info")
                        logger.info("Connection validated successfully")
                        return _ableton_connection
                    except Exception as e:
                        logger.error(f"Connection validation failed: {str(e)}")
                        _ableton_connection.disconnect()
                        _ableton_connection = None
                        # Continue to next attempt
                else:
                    _ableton_connection = None
            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {str(e)}")
                if _ableton_connection:
                    _ableton_connection.disconnect()
                    _ableton_connection = None
            
            # Wait before trying again, but only if we have more attempts left
            if attempt < max_attempts:
                import time
                time.sleep(1.0)
        
        # If we get here, all connection attempts failed
        if _ableton_connection is None:
            logger.error("Failed to connect to Ableton after multiple attempts")
            raise Exception("Could not connect to Ableton. Make sure the Remote Script is running.")
    
    return _ableton_connection


# Core Tool endpoints

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
def get_device_parameters(
    ctx: Context,
    track_index: int,
    device_index: int,
    query: str = None,
    include_host_names: bool = False,
) -> str:
    """
    Get parameters of a device on a track (Live devices and configured VST/AU knobs).

    Values are normalized 0.0–1.0. For plug-ins (Serum 2, etc.) only
    parameters in Live's Configure panel appear here (about 128 max). Live does
    not group those sliders; this tool adds inferred `groups` from names
    (Oscillator A/B/C, Filter 1, Envelope 1, Macros, …). Use query="Oscillator A"
    or query="Filter 1" to fetch one group.

    There is no LOM command to auto-add every host-automatable knob. After
    Configure, save Default Configuration or an .adg rack so new instances keep
    the list.

    Parameters:
    - track_index: Track index (-1 master, -2/-3 returns)
    - device_index: Device index on the track
    - query: Optional filter on name, display_value, or group (e.g. "Filter 1", "Macro")
    - include_host_names: If true, also list PluginDevice.get_parameter_names()
      (names the plug-in reports; still not settable until Configured)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "include_host_names": include_host_names,
        }
        if query:
            payload["query"] = query
        result = ableton.send_command("get_device_parameters", payload)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device parameters: {str(e)}")
        return f"Error getting device parameters: {str(e)}"

@mcp.tool()
def set_device_parameter(
    ctx: Context,
    track_index: int,
    device_index: int,
    value: float,
    parameter_index: int = None,
    parameter_name: str = None,
) -> str:
    """
    Set a device parameter using a normalized value (0.0 to 1.0).
    Prefer parameter_name for VSTs ("Filter 1 Freq", "Macro 1"). Do not reuse
    parameter_index across instances — Configure mappings differ and indices move.
    Missing names mean that knob is not in this instance's Configure panel.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    - value: Normalized value between 0.0 and 1.0
    - parameter_index: Optional parameter index (from get_device_parameters)
    - parameter_name: Optional parameter name (case-insensitive; unique substring ok)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "value": value,
        }
        if parameter_index is not None:
            payload["parameter_index"] = parameter_index
        if parameter_name:
            payload["parameter_name"] = parameter_name
        result = ableton.send_command("set_device_parameter", payload)
        param_name = result.get("parameter_name", "unknown")
        actual_value = result.get("value", value)
        display = result.get("display_value")
        extra = f" ({display})" if display not in (None, "") else ""
        return f"Set '{param_name}' to {actual_value}{extra} (normalized: {value})"
    except Exception as e:
        logger.error(f"Error setting device parameter: {str(e)}")
        return f"Error setting device parameter: {str(e)}"

@mcp.tool()
def batch_set_device_parameters(
    ctx: Context,
    track_index: int,
    device_index: int,
    values: List[float],
    parameter_indices: List[int] = None,
    parameter_names: List[str] = None,
) -> str:
    """
    Set multiple device parameters at once using normalized values (0.0 to 1.0).
    Pass parameter_names (preferred for VSTs) or parameter_indices.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    - values: List of normalized values (0.0 to 1.0)
    - parameter_indices: Optional list of parameter indices
    - parameter_names: Optional list of parameter names (same length as values)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "values": values,
        }
        if parameter_indices is not None:
            payload["parameter_indices"] = parameter_indices
        if parameter_names is not None:
            payload["parameter_names"] = parameter_names
        result = ableton.send_command("batch_set_device_parameters", payload)
        updated_count = result.get("updated_count", 0)
        skipped = result.get("skipped") or []
        params = result.get("parameters", [])
        details = ", ".join([f"{p['name']}={p['value']:.2f}" for p in params])
        msg = f"Updated {updated_count} parameters: {details}" if details else f"Updated {updated_count} parameters"
        if skipped:
            miss = ", ".join(str(s.get("name")) for s in skipped)
            msg += f". Skipped {len(skipped)} not configured on this instance: {miss}"
        return msg
    except Exception as e:
        logger.error(f"Error batch setting device parameters: {str(e)}")
        return f"Error batch setting device parameters: {str(e)}"

@mcp.tool()
def set_plugin_preset(
    ctx: Context,
    track_index: int,
    device_index: int,
    preset_index: int = None,
    preset_name: str = None,
) -> str:
    """
    Select a VST/AU host program-bank preset (PluginDevice.selected_preset_index).

    This is NOT Serum .serumpreset files. VST3 instruments often expose an empty
    bank. Use get_device_parameters to see `presets`.
    """
    try:
        ableton = get_ableton_connection()
        payload = {"track_index": track_index, "device_index": device_index}
        if preset_index is not None:
            payload["preset_index"] = preset_index
        if preset_name:
            payload["preset_name"] = preset_name
        result = ableton.send_command("set_plugin_preset", payload)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting plugin preset: {str(e)}")
        return f"Error setting plugin preset: {str(e)}"

@mcp.tool()
def insert_device(
    ctx: Context,
    track_index: int,
    device_name: str,
    target_index: Optional[int] = None,
) -> str:
    """Insert a native Live device by name at an optional device index.

    Requires Live 12.3+ and Track.insert_device. VST/AU and Max devices remain
    browser/.adg workflows; track_index preserves -1 master and -2/-3 return semantics.
    """
    try:
        params = {
            "track_index": track_index,
            "device_name": device_name,
        }
        if target_index is not None:
            params["target_index"] = target_index
        result = get_ableton_connection().send_command("insert_device", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error inserting device: {str(e)}")
        return f"Error inserting device: {str(e)}"

@mcp.tool()
def load_instrument_or_effect(ctx: Context, track_index: int, uri: str, clip_index: int = -1) -> str:
    """
    Load an instrument or effect onto a track using its URI.
    Use track_index -1 for the master track.

    MIDI effects (Chord, Scale, Arpeggiator) load via get_browser_items_at_path("midi_effects")
    then this tool; Live inserts MIDI FX before the instrument. Use move_device only to
    reorder MIDI effects among themselves or audio effects — Live cannot place an
    instrument before MIDI effects.

    Parameters:
    - track_index: The index of the track to load on (-1 for master)
    - uri: The URI of the instrument or effect to load (e.g., 'query:Synths#Instrument%20Rack:Bass:FileId_5116')
    - clip_index: Optional clip slot index to select before loading (needed for .alc audio clips). Default -1 means no clip slot selection.
    """
    try:
        ableton = get_ableton_connection()
        cmd_params = {
            "track_index": track_index,
            "item_uri": uri
        }
        if clip_index >= 0:
            cmd_params["clip_index"] = clip_index
        result = ableton.send_command("load_browser_item", cmd_params)
        
        # Check if the instrument was loaded successfully
        if result.get("loaded", False):
            new_devices = result.get("new_devices", [])
            if new_devices:
                return f"Loaded instrument with URI '{uri}' on track {track_index}. New devices: {', '.join(new_devices)}"
            else:
                devices = result.get("devices_after", [])
                return f"Loaded instrument with URI '{uri}' on track {track_index}. Devices on track: {', '.join(devices)}"
        else:
            return f"Failed to load instrument with URI '{uri}'"
    except Exception as e:
        logger.error(f"Error loading instrument by URI: {str(e)}")
        return f"Error loading instrument by URI: {str(e)}"

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
def get_browser_tree(ctx: Context, category_type: str = "all") -> str:
    """
    Get a hierarchical tree of browser categories from Ableton.
    
    Parameters:
    - category_type: Type of categories to get ('all', 'instruments', 'sounds', 'drums',
                     'audio_effects', 'midi_effects', 'user_folders').
                     user_folders lists Places roots (e.g. user_folders/AudioAssets).
                     Remote Script only — the Max for Live backend does not expose Places.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_tree", {
            "category_type": category_type
        })
        
        # Check if we got any categories
        if "available_categories" in result and len(result.get("categories", [])) == 0:
            available_cats = result.get("available_categories", [])
            return (f"No categories found for '{category_type}'. "
                   f"Available browser categories: {', '.join(available_cats)}")
        
        # Format the tree in a more readable way
        total_folders = result.get("total_folders", 0)
        formatted_output = f"Browser tree for '{category_type}' (showing {total_folders} folders):\n\n"
        
        def format_tree(item, indent=0):
            output = ""
            if item:
                prefix = "  " * indent
                name = item.get("name", "Unknown")
                path = item.get("path", "")
                has_more = item.get("has_more", False)
                
                # Add this item
                output += f"{prefix}• {name}"
                if path:
                    output += f" (path: {path})"
                if has_more:
                    output += " [...]"
                output += "\n"
                
                # Add children
                for child in item.get("children", []):
                    output += format_tree(child, indent + 1)
            return output
        
        # Format each category
        for category in result.get("categories", []):
            formatted_output += format_tree(category)
            formatted_output += "\n"
        
        return formatted_output
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        else:
            logger.error(f"Error getting browser tree: {error_msg}")
            return f"Error getting browser tree: {error_msg}"

@mcp.tool()
def get_browser_items_at_path(ctx: Context, path: str) -> str:
    """
    Get browser items at a specific path in Ableton's browser.
    
    Parameters:
    - path: Path in the format "category/folder/subfolder"
            where category is one of the available browser categories in Ableton.
            user_folders lists Places roots (e.g. user_folders/AudioAssets).
            Remote Script only.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {
            "path": path
        })
        
        # Check if there was an error with available categories
        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        elif "Unknown or unavailable category" in error_msg:
            logger.error(f"Invalid browser category: {error_msg}")
            return f"Error: {error_msg}. Please check the available categories using get_browser_tree."
        elif "Path part" in error_msg and "not found" in error_msg:
            logger.error(f"Path not found: {error_msg}")
            return f"Error: {error_msg}. Please check the path and try again."
        else:
            logger.error(f"Error getting browser items at path: {error_msg}")
            return f"Error getting browser items at path: {error_msg}"

@mcp.tool()
def load_drum_kit(ctx: Context, track_index: int, rack_uri: str, kit_path: str) -> str:
    """
    Load a drum rack and then load a specific drum kit into it.
    
    Parameters:
    - track_index: The index of the track to load on
    - rack_uri: The URI of the drum rack to load (e.g., 'Drums/Drum Rack')
    - kit_path: Path to the drum kit inside the browser (e.g., 'drums/acoustic/kit1')
    """
    try:
        ableton = get_ableton_connection()
        
        # Step 1: Load the drum rack
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": rack_uri
        })
        
        if not result.get("loaded", False):
            return f"Failed to load drum rack with URI '{rack_uri}'"
        
        # Step 2: Get the drum kit items at the specified path
        kit_result = ableton.send_command("get_browser_items_at_path", {
            "path": kit_path
        })
        
        if "error" in kit_result:
            return f"Loaded drum rack but failed to find drum kit: {kit_result.get('error')}"
        
        # Step 3: Find a loadable drum kit
        kit_items = kit_result.get("items", [])
        loadable_kits = [item for item in kit_items if item.get("is_loadable", False)]
        
        if not loadable_kits:
            return f"Loaded drum rack but no loadable drum kits found at '{kit_path}'"
        
        # Step 4: Load the first loadable kit
        kit_uri = loadable_kits[0].get("uri")
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": kit_uri
        })
        
        return f"Loaded drum rack and kit '{loadable_kits[0].get('name')}' on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading drum kit: {str(e)}")
        return f"Error loading drum kit: {str(e)}"

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
def delete_device(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Delete a device from a track.

    Parameters:
    - track_index: The index of the track (use -1 for master, -2/-3 for returns)
    - device_index: The index of the device to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_device", {
            "track_index": track_index,
            "device_index": device_index
        })
        return f"Deleted device '{result.get('deleted_device', '')}' ({result.get('device_count', '?')} devices remaining)"
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        return f"Error deleting device: {str(e)}"

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
def set_device_enabled(ctx: Context, track_index: int, device_index: int, enabled: bool) -> str:
    """Enable or bypass a device (track_index -1 = master, -2/-3 = returns). Use it to A/B an effect."""
    try:
        result = get_ableton_connection().send_command("set_device_enabled", {
            "track_index": track_index, "device_index": device_index, "enabled": enabled})
        return f"{'Enabled' if enabled else 'Bypassed'} {result.get('device_name', 'device')}"
    except Exception as e:
        logger.error(f"Error setting device enabled: {str(e)}")
        return f"Error setting device enabled: {str(e)}"

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
def stop_all_clips(ctx: Context, quantized: bool = True) -> str:
    """Stop every playing session clip (quantized = at the next launch-quantization point)."""
    try:
        get_ableton_connection().send_command("stop_all_clips", {"quantized": quantized})
        return "Stopped all clips"
    except Exception as e:
        logger.error(f"Error stopping all clips: {str(e)}")
        return f"Error stopping all clips: {str(e)}"

@mcp.tool()
def get_drum_pads(ctx: Context, track_index: int, device_index: int = 0) -> str:
    """List the filled pads of a Drum Rack: MIDI note, pad name, device. Read this before programming a kit."""
    try:
        result = get_ableton_connection().send_command("get_drum_pads", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting drum pads: {str(e)}")
        return f"Error getting drum pads: {str(e)}"

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
def get_simpler_sample(ctx: Context, track_index: int, device_index: int) -> str:
    """Read a SimplerDevice's sample path and marker positions in integer sample frames.

    Requires a Simpler device and a Remote Script backend exposing its Sample properties.
    """
    try:
        result = get_ableton_connection().send_command("get_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting Simpler sample: {str(e)}")
        return f"Error getting Simpler sample: {str(e)}"

@mcp.tool()
def set_simpler_sample_window(
    ctx: Context,
    track_index: int,
    device_index: int,
    start_marker: Optional[int] = None,
    end_marker: Optional[int] = None,
) -> str:
    """Set optional Simpler sample start/end markers, expressed as integer sample frames.

    Requires a SimplerDevice and backend support for Sample.start_marker/end_marker;
    omitted markers remain unchanged.
    """
    try:
        params = {
            "track_index": track_index,
            "device_index": device_index,
        }
        if start_marker is not None:
            params["start_marker"] = start_marker
        if end_marker is not None:
            params["end_marker"] = end_marker
        result = get_ableton_connection().send_command("set_simpler_sample_window", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting Simpler sample window: {str(e)}")
        return f"Error setting Simpler sample window: {str(e)}"

@mcp.tool()
def replace_simpler_sample(ctx: Context, track_index: int, device_index: int, file_path: str) -> str:
    """Replace a Simpler sample from an absolute file path.

    Uses SimplerDevice.replace_sample and requires Live 12.4+; pre-12.4 builds
    must return a clear backend error. The path is passed unchanged to Live.
    """
    try:
        result = get_ableton_connection().send_command("replace_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
            "file_path": file_path,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error replacing Simpler sample: {str(e)}")
        return f"Error replacing Simpler sample: {str(e)}"

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
def get_device_sidechain(ctx: Context, track_index: int, device_index: int) -> str:
    """Read external sidechain routing on a CompressorDevice (Compressor, Glue Compressor).

    Returns available routing types/channels and the current source. Other device classes
    have no sidechain API. track_index -1 = master, -2/-3 = returns.
    """
    try:
        result = get_ableton_connection().send_command("get_device_sidechain", {
            "track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device sidechain: {str(e)}")
        return f"Error getting device sidechain: {str(e)}"

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
def get_cue_points(ctx: Context) -> str:
    """List arrangement cue points (name, time in beats). Use jump_to_cue / toggle_cue to navigate or set them."""
    try:
        result = get_ableton_connection().send_command("get_cue_points")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting cue points: {str(e)}")
        return f"Error getting cue points: {str(e)}"

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
def move_device(ctx: Context, track_index: int, device_index: int, target_index: int) -> str:
    """Reorder a device on a track (0 = leftmost).

    Use this to reorder MIDI effects among themselves, or audio effects.
    load_instrument_or_effect already inserts MIDI FX before the instrument.
    Live cannot place an instrument before MIDI effects (Couldn't move device).
    """
    try:
        result = get_ableton_connection().send_command("move_device", {
            "track_index": track_index, "device_index": device_index, "target_index": target_index})
        return f"Moved device {device_index} to {result.get('target_index', target_index)} on track {track_index}"
    except Exception as e:
        logger.error(f"Error moving device: {str(e)}")
        return f"Error moving device: {str(e)}"

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

@mcp.tool()
def set_device_sidechain(ctx: Context, track_index: int, device_index: int, routing_type_name: str, channel_name: str = None) -> str:
    """Set the external sidechain source on a CompressorDevice (Compressor, Glue Compressor).

    Use get_device_sidechain first for available routing_type_name / channel_name values
    (e.g. a kick track). Other device classes have no sidechain API.
    """
    try:
        params = {"track_index": track_index, "device_index": device_index,
                  "routing_type_name": routing_type_name}
        if channel_name is not None:
            params["channel_name"] = channel_name
        result = get_ableton_connection().send_command("set_device_sidechain", params)
        return f"Sidechain '{routing_type_name}' / {result.get('channel_name', channel_name)}"
    except Exception as e:
        logger.error(f"Error setting device sidechain: {str(e)}")
        return f"Error setting device sidechain: {str(e)}"

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
def capture_and_insert_scene(ctx: Context) -> str:
    """Capture currently playing session clips into a new scene (song.capture_and_insert_scene)."""
    try:
        result = get_ableton_connection().send_command("capture_and_insert_scene")
        return f"Captured scene '{result.get('name', '')}' at index {result.get('scene_index', '')}"
    except Exception as e:
        logger.error(f"Error capturing and inserting scene: {str(e)}")
        return f"Error capturing and inserting scene: {str(e)}"

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


def main():
    """Run the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()
