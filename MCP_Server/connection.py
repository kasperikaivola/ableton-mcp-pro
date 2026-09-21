import json
import socket
from dataclasses import dataclass
from typing import Any, Dict

from .runtime import logger

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



