# AbletonMCP/init.py
from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import socket
import json
import threading
import time
import traceback

# Change queue import for Python 2
try:
    import Queue as queue  # Python 2
except ImportError:
    import queue  # Python 3

try:
    _INTEGER_TYPES = (int, long)
except NameError:
    _INTEGER_TYPES = (int,)

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

try:
    from .plugin_params import (
        attach_groups,
        classify_device,
        filter_parameters,
        find_parameter,
        is_plugin_class,
        mapping_coverage,
        normalize_param_key,
        plugin_configure_note,
        try_find_parameter,
    )
except (ImportError, ValueError):
    from plugin_params import (
        attach_groups,
        classify_device,
        filter_parameters,
        find_parameter,
        is_plugin_class,
        mapping_coverage,
        normalize_param_key,
        plugin_configure_note,
        try_find_parameter,
    )

# Constants for socket communication
DEFAULT_PORT = 9877
HOST = "localhost"

_ARRANGEMENT_ENVELOPE_NOTE = (
    "Arrangement clip automation is not in the public LOM (it lives on the track). "
    "Arrangement clips only have modulation, which this API does not expose. "
    "Use session clips for clip envelopes."
)
_MOVE_DEVICE_INSTRUMENT_MSG = (
    "Live cannot place an instrument before MIDI effects. "
    "load_instrument_or_effect already inserts MIDI FX before the instrument; "
    "use move_device only to reorder MIDI effects (or audio effects)."
)

def create_instance(c_instance):
    """Create and return the AbletonMCP script instance"""
    return AbletonMCP(c_instance)

class AbletonMCP(ControlSurface):
    """AbletonMCP Remote Script for Ableton Live"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        ControlSurface.__init__(self, c_instance)
        self.log_message("AbletonMCP Remote Script initializing...")
        
        # Socket server for communication
        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False
        
        # Cache the song reference for easier access
        self._song = self.song()
        
        # Start the socket server
        self.start_server()
        
        self.log_message("AbletonMCP initialized")
        
        # Show a message in Ableton
        self.show_message("AbletonMCP: Listening for commands on port " + str(DEFAULT_PORT))
    
    def disconnect(self):
        """Called when Ableton closes or the control surface is removed"""
        self.log_message("AbletonMCP disconnecting...")
        self.running = False
        
        # Stop the server
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # Wait for the server thread to exit
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
            
        # Clean up any client threads
        for client_thread in self.client_threads[:]:
            if client_thread.is_alive():
                # We don't join them as they might be stuck
                self.log_message("Client thread still alive during disconnect")
        
        ControlSurface.disconnect(self)
        self.log_message("AbletonMCP disconnected")
    
    def start_server(self):
        """Start the socket server in a separate thread"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)  # Allow up to 5 pending connections
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("AbletonMCP: Error starting server - " + str(e))
    
    def _server_thread(self):
        """Server thread implementation - handles client connections"""
        try:
            self.log_message("Server thread started")
            # Set a timeout to allow regular checking of running flag
            self.server.settimeout(1.0)
            
            while self.running:
                try:
                    # Accept connections with timeout
                    client, address = self.server.accept()
                    self.log_message("Connection accepted from " + str(address))
                    self.show_message("AbletonMCP: Client connected")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Keep track of client threads
                    self.client_threads.append(client_thread)
                    
                    # Clean up finished client threads
                    self.client_threads = [t for t in self.client_threads if t.is_alive()]
                    
                except socket.timeout:
                    # No connection yet, just continue
                    continue
                except Exception as e:
                    if self.running:  # Only log if still running
                        self.log_message("Server accept error: " + str(e))
                    time.sleep(0.5)
            
            self.log_message("Server thread stopped")
        except Exception as e:
            self.log_message("Server thread error: " + str(e))
    
    def _handle_client(self, client):
        """Handle communication with a connected client"""
        self.log_message("Client handler started")
        client.settimeout(None)  # No timeout for client socket
        buffer = ''  # Changed from b'' to '' for Python 2
        
        try:
            while self.running:
                try:
                    # Receive data
                    data = client.recv(8192)
                    
                    if not data:
                        # Client disconnected
                        self.log_message("Client disconnected")
                        break
                    
                    # Accumulate data in buffer with explicit encoding/decoding
                    try:
                        # Python 3: data is bytes, decode to string
                        buffer += data.decode('utf-8')
                    except AttributeError:
                        # Python 2: data is already string
                        buffer += data
                    
                    try:
                        # Try to parse command from buffer
                        command = json.loads(buffer)  # Removed decode('utf-8')
                        buffer = ''  # Clear buffer after successful parse
                        
                        self.log_message("Received command: " + str(command.get("type", "unknown")))
                        
                        # Process the command and get response
                        response = self._process_command(command)
                        
                        # Send the response with explicit encoding
                        try:
                            # Python 3: encode string to bytes
                            client.sendall(json.dumps(response).encode('utf-8'))
                        except AttributeError:
                            # Python 2: string is already bytes
                            client.sendall(json.dumps(response))
                    except ValueError:
                        # Incomplete data, wait for more
                        continue
                        
                except Exception as e:
                    self.log_message("Error handling client data: " + str(e))
                    self.log_message(traceback.format_exc())
                    
                    # Send error response if possible
                    error_response = {
                        "status": "error",
                        "message": str(e)
                    }
                    try:
                        # Python 3: encode string to bytes
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except AttributeError:
                        # Python 2: string is already bytes
                        client.sendall(json.dumps(error_response))
                    except:
                        # If we can't send the error, the connection is probably dead
                        break
                    
                    # For serious errors, break the loop
                    if not isinstance(e, ValueError):
                        break
        except Exception as e:
            self.log_message("Error in client handler: " + str(e))
        finally:
            try:
                client.close()
            except:
                pass
            self.log_message("Client handler stopped")
    
    def _process_command(self, command):
        """Process a command from the client and return a response"""
        # Refresh song reference — cached ref can become stale after doc swap
        self._song = self.song()
        command_type = command.get("type", "")
        params = command.get("params", {})
        
        # Initialize response
        response = {
            "status": "success",
            "result": {}
        }
        
        try:
            # Route the command to the appropriate handler
            if command_type == "get_session_info":
                response["result"] = self._get_session_info()
            elif command_type == "get_track_info":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_info(track_index)
            elif command_type == "get_track_routing":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_routing(track_index)
            # Commands that modify Live's state should be scheduled on the main thread
            elif command_type == "get_device_parameters":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_device_parameters(
                    track_index, device_index,
                    params.get("query"),
                    params.get("include_host_names", False))
            elif command_type == "get_arrangement_info":
                response["result"] = self._get_arrangement_info()
            elif command_type == "get_arrangement_clips":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_arrangement_clips(track_index)
            elif command_type == "get_full_arrangement":
                response["result"] = self._get_full_arrangement()
            elif command_type == "get_clip_notes":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                response["result"] = self._get_clip_notes(track_index, clip_index)
            elif command_type == "get_arrangement_clip_notes":
                track_index = params.get("track_index", 0)
                arrangement_clip_index = params.get("arrangement_clip_index", 0)
                response["result"] = self._get_arrangement_clip_notes(track_index, arrangement_clip_index)
            elif command_type == "get_clip_envelope":
                track_index = params.get("track_index", 0)
                clip_index = params.get("clip_index", 0)
                device_index = params.get("device_index", 0)
                parameter_index = params.get("parameter_index", 0)
                response["result"] = self._get_clip_envelope(track_index, clip_index, device_index, parameter_index,
                                                             params.get("arrangement_clip_index"))
            elif command_type == "get_clip_info":
                response["result"] = self._get_clip_info(params.get("track_index", 0), params.get("clip_index", 0),
                                                         params.get("arrangement_clip_index"))
            elif command_type == "resample_master":
                # Runs on the socket thread: plays the arrangement in real time while recording
                response["result"] = self._resample_master(params.get("seconds"), params.get("name", "master rec"),
                                                           params.get("start_time", 0.0))
            elif command_type == "get_drum_pads":
                track_index = params.get("track_index", 0)
                device_index = params.get("device_index", 0)
                response["result"] = self._get_drum_pads(track_index, device_index)
            elif command_type == "get_groove_pool":
                response["result"] = self._get_groove_pool()
            elif command_type == "get_device_sidechain":
                response["result"] = self._get_device_sidechain(params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_rack_chains":
                response["result"] = self._get_rack_chains(params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_rack_macros":
                response["result"] = self._get_rack_macros(params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_simpler_sample":
                response["result"] = self._get_simpler_sample(params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_application_info":
                response["result"] = self._get_application_info()
            elif command_type == "get_cue_points":
                response["result"] = self._get_cue_points()
            elif command_type == "get_warp_markers":
                response["result"] = self._get_warp_markers(params.get("track_index", 0), params.get("clip_index", 0),
                                                           params.get("arrangement_clip_index"))
            elif command_type == "convert_clip_time":
                response["result"] = self._convert_clip_time(params.get("track_index", 0), params.get("clip_index", 0),
                                                             params.get("beat_time"), params.get("sample_time"),
                                                             params.get("arrangement_clip_index"))
            elif command_type == "record_arrangement":
                # Runs on socket thread with schedule_message for main thread ops
                sections = params.get("sections", [])
                start_time = params.get("start_time", 0.0)
                response["result"] = self._record_arrangement(sections, start_time)
            elif command_type in ["create_midi_track", "set_track_name",
                                 "create_clip", "create_arrangement_audio_clip", "create_arrangement_audio_clips_batch",
                                 "create_arrangement_midi_clip", "delete_arrangement_clip",
                                 "add_notes_to_clip", "capture_midi", "set_clip_name",
                                 "set_tempo", "fire_clip", "stop_clip",
                                 "start_playback", "stop_playback", "play_arrangement",
                                 "load_browser_item",
                                 "load_instrument_or_effect",
                                 "set_device_parameter", "batch_set_device_parameters",
                                 "set_plugin_preset",
                                 "set_track_volume", "set_track_panning",
                                 "fire_scene", "set_song_time", "set_record_mode",
                                 "set_arrangement_overdub", "set_back_to_arranger",
                                 "set_arrangement_loop",
                                 "set_track_mute", "set_track_solo",
                                 "delete_clip", "duplicate_clip",
                                 "create_scene", "delete_scene", "set_scene_name",
                                 "create_audio_track", "delete_track",
                                 "delete_device", "duplicate_track", "set_clip_loop",
                                 "set_track_arm", "set_send_level", "set_time_signature",
                                 "set_track_monitoring", "set_track_input_routing",
                                 "set_track_output_routing",
                                 "set_metronome", "set_clip_envelope", "clear_clip_envelope",
                                 "undo", "redo",
                                 "remove_notes", "quantize_clip", "duplicate_clip_loop", "duplicate_region",
                                 "set_device_enabled", "create_return_track", "delete_return_track",
                                 "stop_all_clips", "set_clip_gain", "set_clip_pitch",
                                 "set_clip_warping", "set_clip_warp_mode",
                                 "move_device", "set_groove_amount", "apply_groove", "clear_clip_groove",
                                 "set_device_sidechain", "insert_rack_chain", "set_chain_mixer",
                                 "add_macro", "remove_macro", "randomize_macros",
                                 "store_macro_variation", "recall_macro_variation", "delete_macro_variation",
                                 "duplicate_clip_to_arrangement", "insert_device",
                                 "set_simpler_sample_window", "replace_simpler_sample",
                                 "press_current_dialog_button", "apply_note_modifications",
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
                                 "set_scene_tempo", "set_scene_signature", "set_cue_volume"]:
                # Use a thread-safe approach with a response queue
                response_queue = queue.Queue()
                
                # Define a function to execute on the main thread
                def main_thread_task():
                    try:
                        result = None
                        if command_type == "create_midi_track":
                            index = params.get("index", -1)
                            result = self._create_midi_track(index)
                        elif command_type == "set_track_name":
                            track_index = params.get("track_index", 0)
                            name = params.get("name", "")
                            result = self._set_track_name(track_index, name)
                        elif command_type == "set_track_monitoring":
                            track_index = params.get("track_index", 0)
                            state = params.get("state", 1)
                            result = self._set_track_monitoring(track_index, state)
                        elif command_type == "set_track_input_routing":
                            track_index = params.get("track_index", 0)
                            routing_type_name = params.get("routing_type_name", "")
                            result = self._set_track_input_routing(track_index, routing_type_name, params.get("channel_name"))
                        elif command_type == "set_track_output_routing":
                            track_index = params.get("track_index", 0)
                            routing_type_name = params.get("routing_type_name", "")
                            result = self._set_track_output_routing(track_index, routing_type_name)
                        elif command_type == "create_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            length = params.get("length", 4.0)
                            result = self._create_clip(track_index, clip_index, length)
                        elif command_type == "create_arrangement_audio_clip":
                            track_index = params.get("track_index", 0)
                            file_path = params.get("file_path", "")
                            time = params.get("time", 0.0)
                            length = params.get("length", None)
                            start_offset = params.get("start_offset", None)
                            result = self._create_arrangement_audio_clip(track_index, file_path, time, length, start_offset)
                        elif command_type == "create_arrangement_audio_clips_batch":
                            result = self._create_arrangement_audio_clips_batch(
                                params.get("track_index", 0), params.get("file_path", ""), params.get("times", []),
                                params.get("length", None), params.get("start_offset", None))
                        elif command_type == "create_arrangement_midi_clip":
                            track_index = params.get("track_index", 0)
                            time = params.get("time", 0.0)
                            length = params.get("length", 4.0)
                            notes = params.get("notes", None)
                            result = self._create_arrangement_midi_clip(track_index, time, length, notes)
                        elif command_type == "delete_arrangement_clip":
                            track_index = params.get("track_index", 0)
                            arrangement_clip_index = params.get("arrangement_clip_index", 0)
                            result = self._delete_arrangement_clip(track_index, arrangement_clip_index)
                        elif command_type == "add_notes_to_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            notes = params.get("notes", [])
                            arrangement_clip_index = params.get("arrangement_clip_index", None)
                            result = self._add_notes_to_clip(track_index, clip_index, notes,
                                                             arrangement_clip_index)
                        elif command_type == "apply_note_modifications":
                            result = self._apply_note_modifications(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("notes", []),
                                params.get("arrangement_clip_index"))
                        elif command_type == "capture_midi":
                            destination = params.get("destination", 0)
                            result = self._capture_midi(destination)
                        elif command_type == "set_clip_name":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            name = params.get("name", "")
                            result = self._set_clip_name(track_index, clip_index, name)
                        elif command_type == "set_tempo":
                            tempo = params.get("tempo", 120.0)
                            result = self._set_tempo(tempo)
                        elif command_type == "fire_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._fire_clip(track_index, clip_index)
                        elif command_type == "stop_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._stop_clip(track_index, clip_index)
                        elif command_type == "start_playback":
                            result = self._start_playback()
                        elif command_type == "stop_playback":
                            result = self._stop_playback()
                        elif command_type == "play_arrangement":
                            time = params.get("time", None)
                            result = self._play_arrangement(time)
                        elif command_type == "load_instrument_or_effect":
                            track_index = params.get("track_index", 0)
                            uri = params.get("uri", "")
                            clip_index = params.get("clip_index", None)
                            result = self._load_browser_item(track_index, uri, clip_index=clip_index)
                        elif command_type == "load_browser_item":
                            track_index = params.get("track_index", 0)
                            item_uri = params.get("item_uri", "")
                            clip_index = params.get("clip_index", None)
                            result = self._load_browser_item(track_index, item_uri, clip_index=clip_index)
                        elif command_type == "set_device_parameter":
                            result = self._set_device_parameter(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("parameter_index"),
                                params.get("value", 0.0),
                                params.get("parameter_name"))
                        elif command_type == "batch_set_device_parameters":
                            result = self._batch_set_device_parameters(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("parameter_indices"),
                                params.get("values", []),
                                params.get("parameter_names"))
                        elif command_type == "set_plugin_preset":
                            result = self._set_plugin_preset(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("preset_index"),
                                params.get("preset_name"))
                        elif command_type == "set_track_volume":
                            track_index = params.get("track_index", 0)
                            volume = params.get("volume", 0.85)
                            result = self._set_track_volume(track_index, volume)
                        elif command_type == "set_track_panning":
                            track_index = params.get("track_index", 0)
                            panning = params.get("panning", 0.0)
                            result = self._set_track_panning(track_index, panning)
                        elif command_type == "fire_scene":
                            scene_index = params.get("scene_index", 0)
                            result = self._fire_scene(scene_index)
                        elif command_type == "set_song_time":
                            time = params.get("time", 0.0)
                            result = self._set_song_time(time)
                        elif command_type == "set_record_mode":
                            on = params.get("on", False)
                            result = self._set_record_mode(on)
                        elif command_type == "set_arrangement_overdub":
                            on = params.get("on", False)
                            result = self._set_arrangement_overdub(on)
                        elif command_type == "set_back_to_arranger":
                            result = self._set_back_to_arranger(params.get("value", False))
                        elif command_type == "set_arrangement_loop":
                            on = params.get("on", True)
                            start = params.get("start", 0.0)
                            length = params.get("length", 16.0)
                            result = self._set_arrangement_loop(on, start, length)
                        elif command_type == "set_track_mute":
                            track_index = params.get("track_index", 0)
                            mute = params.get("mute", False)
                            result = self._set_track_mute(track_index, mute)
                        elif command_type == "set_track_solo":
                            track_index = params.get("track_index", 0)
                            solo = params.get("solo", False)
                            result = self._set_track_solo(track_index, solo)
                        elif command_type == "delete_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._delete_clip(track_index, clip_index)
                        elif command_type == "duplicate_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            target_index = params.get("target_index", -1)
                            result = self._duplicate_clip(track_index, clip_index, target_index)
                        elif command_type == "duplicate_clip_to_arrangement":
                            result = self._duplicate_clip_to_arrangement(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("destination_time"))
                        elif command_type == "insert_device":
                            result = self._insert_device(
                                params.get("track_index", 0),
                                params.get("device_name", ""),
                                params.get("target_index"))
                        elif command_type == "create_scene":
                            index = params.get("index", -1)
                            result = self._create_scene(index)
                        elif command_type == "delete_scene":
                            scene_index = params.get("scene_index", 0)
                            result = self._delete_scene(scene_index)
                        elif command_type == "set_scene_name":
                            scene_index = params.get("scene_index", 0)
                            name = params.get("name", "")
                            result = self._set_scene_name(scene_index, name)
                        elif command_type == "create_audio_track":
                            index = params.get("index", -1)
                            result = self._create_audio_track(index)
                        elif command_type == "delete_track":
                            track_index = params.get("track_index", 0)
                            result = self._delete_track(track_index)
                        elif command_type == "delete_device":
                            track_index = params.get("track_index", 0)
                            device_index = params.get("device_index", 0)
                            result = self._delete_device(track_index, device_index)
                        elif command_type == "duplicate_track":
                            track_index = params.get("track_index", 0)
                            result = self._duplicate_track(track_index)
                        elif command_type == "set_clip_loop":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            loop_start = params.get("loop_start", None)
                            loop_end = params.get("loop_end", None)
                            looping = params.get("looping", None)
                            result = self._set_clip_loop(track_index, clip_index, loop_start, loop_end, looping)
                        elif command_type == "set_track_arm":
                            track_index = params.get("track_index", 0)
                            arm = params.get("arm", False)
                            result = self._set_track_arm(track_index, arm)
                        elif command_type == "set_send_level":
                            track_index = params.get("track_index", 0)
                            send_index = params.get("send_index", 0)
                            value = params.get("value", 0.0)
                            result = self._set_send_level(track_index, send_index, value)
                        elif command_type == "set_time_signature":
                            numerator = params.get("numerator", 4)
                            denominator = params.get("denominator", 4)
                            result = self._set_time_signature(numerator, denominator)
                        elif command_type == "set_metronome":
                            on = params.get("on", False)
                            result = self._set_metronome(on)
                        elif command_type == "set_clip_envelope":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            parameter_index = params.get("parameter_index", 0)
                            device_index = params.get("device_index", 0)
                            points = params.get("points", [])
                            result = self._set_clip_envelope(track_index, clip_index, device_index, parameter_index, points,
                                                             params.get("arrangement_clip_index"))
                        elif command_type == "clear_clip_envelope":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            parameter_index = params.get("parameter_index", 0)
                            device_index = params.get("device_index", 0)
                            result = self._clear_clip_envelope(track_index, clip_index, device_index, parameter_index,
                                                               params.get("arrangement_clip_index"))
                        elif command_type == "undo":
                            result = self._undo()
                        elif command_type == "redo":
                            result = self._redo()
                        elif command_type == "remove_notes":
                            result = self._remove_notes(params.get("track_index", 0), params.get("clip_index", 0),
                                                        params.get("from_pitch", 0), params.get("pitch_span", 128),
                                                        params.get("from_time", 0.0), params.get("time_span", -1.0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "quantize_clip":
                            result = self._quantize_clip(params.get("track_index", 0), params.get("clip_index", 0),
                                                         params.get("grid", 5), params.get("strength", 1.0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "duplicate_clip_loop":
                            result = self._duplicate_clip_loop(params.get("track_index", 0), params.get("clip_index", 0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "duplicate_region":
                            result = self._duplicate_region(params.get("track_index", 0), params.get("clip_index", 0),
                                                            params.get("region_start", 0.0), params.get("region_length", 4.0),
                                                            params.get("destination_time", 4.0), params.get("pitch", -1),
                                                            params.get("transposition_amount", 0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "set_device_enabled":
                            result = self._set_device_enabled(params.get("track_index", 0), params.get("device_index", 0),
                                                              params.get("enabled", True))
                        elif command_type == "add_macro":
                            result = self._add_macro(params.get("track_index", 0), params.get("device_index", 0))
                        elif command_type == "remove_macro":
                            result = self._remove_macro(params.get("track_index", 0), params.get("device_index", 0))
                        elif command_type == "randomize_macros":
                            result = self._randomize_macros(params.get("track_index", 0), params.get("device_index", 0))
                        elif command_type == "store_macro_variation":
                            result = self._store_macro_variation(params.get("track_index", 0), params.get("device_index", 0))
                        elif command_type == "recall_macro_variation":
                            result = self._recall_macro_variation(
                                params.get("track_index", 0), params.get("device_index", 0),
                                params.get("variation_index"))
                        elif command_type == "delete_macro_variation":
                            result = self._delete_macro_variation(
                                params.get("track_index", 0), params.get("device_index", 0),
                                params.get("variation_index"))
                        elif command_type == "set_simpler_sample_window":
                            result = self._set_simpler_sample_window(
                                params.get("track_index", 0), params.get("device_index", 0),
                                params.get("start_marker"), params.get("end_marker"))
                        elif command_type == "replace_simpler_sample":
                            result = self._replace_simpler_sample(
                                params.get("track_index", 0), params.get("device_index", 0),
                                params.get("file_path", ""))
                        elif command_type == "press_current_dialog_button":
                            result = self._press_current_dialog_button(params.get("index"))
                        elif command_type == "create_return_track":
                            result = self._create_return_track()
                        elif command_type == "delete_return_track":
                            result = self._delete_return_track(params.get("index", 0))
                        elif command_type == "stop_all_clips":
                            result = self._stop_all_clips(params.get("quantized", True))
                        elif command_type == "set_clip_gain":
                            result = self._set_clip_gain(params.get("track_index", 0), params.get("clip_index", 0), params.get("gain", 0.0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_pitch":
                            result = self._set_clip_pitch(params.get("track_index", 0), params.get("clip_index", 0),
                                                          params.get("coarse", None), params.get("fine", None), aci=params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_warping":
                            result = self._set_clip_warping(params.get("track_index", 0), params.get("clip_index", 0), params.get("warping", True), aci=params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_warp_mode":
                            result = self._set_clip_warp_mode(params.get("track_index", 0), params.get("clip_index", 0), params.get("warp_mode", 0), aci=params.get("arrangement_clip_index"))
                        elif command_type == "move_device":
                            result = self._move_device(params.get("track_index", 0), params.get("device_index", 0),
                                                       params.get("target_index", 0))
                        elif command_type == "set_groove_amount":
                            result = self._set_groove_amount(params.get("amount", 0.0))
                        elif command_type == "apply_groove":
                            result = self._apply_groove(params.get("track_index", 0), params.get("clip_index", 0),
                                                        params.get("groove_index", 0), params.get("arrangement_clip_index"))
                        elif command_type == "clear_clip_groove":
                            result = self._clear_clip_groove(params.get("track_index", 0), params.get("clip_index", 0),
                                                             params.get("arrangement_clip_index"))
                        elif command_type == "set_device_sidechain":
                            result = self._set_device_sidechain(params.get("track_index", 0), params.get("device_index", 0),
                                                                params.get("routing_type_name", ""), params.get("channel_name"))
                        elif command_type == "insert_rack_chain":
                            result = self._insert_rack_chain(params.get("track_index", 0), params.get("device_index", 0),
                                                             params.get("index", -1), params.get("name"))
                        elif command_type == "set_chain_mixer":
                            result = self._set_chain_mixer(params.get("track_index", 0), params.get("device_index", 0),
                                                           params.get("chain_index", 0), params.get("mute"), params.get("solo"),
                                                           params.get("volume"), params.get("panning"))
                        elif command_type == "capture_and_insert_scene":
                            result = self._capture_and_insert_scene()
                        elif command_type == "crop_clip":
                            result = self._crop_clip(params.get("track_index", 0), params.get("clip_index", 0),
                                                     params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_launch":
                            result = self._set_clip_launch(params.get("track_index", 0), params.get("clip_index", 0),
                                                           params.get("launch_mode"), params.get("launch_quantization"),
                                                           params.get("legato"), params.get("arrangement_clip_index"))
                        elif command_type == "toggle_cue":
                            result = self._toggle_cue()
                        elif command_type == "jump_to_cue":
                            result = self._jump_to_cue(params.get("direction"), params.get("index"))
                        elif command_type == "set_crossfader":
                            result = self._set_crossfader(params.get("value", 0.0))
                        elif command_type == "set_crossfade_assign":
                            result = self._set_crossfade_assign(params.get("track_index", 0), params.get("assign"))
                        elif command_type == "show_view":
                            result = self._show_view(params.get("view_name", ""))
                        elif command_type == "add_warp_marker":
                            result = self._add_warp_marker(params.get("track_index", 0), params.get("clip_index", 0),
                                                           params.get("beat_time", 0.0), params.get("sample_time"),
                                                           params.get("arrangement_clip_index"))
                        elif command_type == "move_warp_marker":
                            result = self._move_warp_marker(params.get("track_index", 0), params.get("clip_index", 0),
                                                            params.get("beat_time", 0.0), params.get("beat_time_distance", 0.0),
                                                            params.get("arrangement_clip_index"))
                        elif command_type == "delete_warp_marker":
                            result = self._delete_warp_marker(params.get("track_index", 0), params.get("clip_index", 0),
                                                              params.get("beat_time", 0.0),
                                                              params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_color":
                            result = self._set_clip_color(params.get("track_index", 0), params.get("clip_index", 0),
                                                          params.get("color_index"), params.get("color"),
                                                          params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_muted":
                            result = self._set_clip_muted(params.get("track_index", 0), params.get("clip_index", 0),
                                                          params.get("muted", False),
                                                          params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_markers":
                            result = self._set_clip_markers(params.get("track_index", 0), params.get("clip_index", 0),
                                                            params.get("start_marker"), params.get("end_marker"),
                                                            params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_signature":
                            result = self._set_clip_signature(params.get("track_index", 0), params.get("clip_index", 0),
                                                              params.get("numerator", 4), params.get("denominator", 4),
                                                              params.get("arrangement_clip_index"))
                        elif command_type == "quantize_pitch":
                            result = self._quantize_pitch(params.get("track_index", 0), params.get("clip_index", 0),
                                                          params.get("pitch", 60), params.get("grid", 5),
                                                          params.get("strength", 1.0),
                                                          params.get("arrangement_clip_index"))
                        elif command_type == "set_clip_ram_mode":
                            result = self._set_clip_ram_mode(params.get("track_index", 0), params.get("clip_index", 0),
                                                             params.get("ram_mode", False),
                                                             params.get("arrangement_clip_index"))
                        elif command_type == "tap_tempo":
                            result = self._tap_tempo()
                        elif command_type == "jump_by":
                            result = self._jump_by(params.get("beats", 0.0))
                        elif command_type == "continue_playing":
                            result = self._continue_playing()
                        elif command_type == "set_session_record":
                            result = self._set_session_record(params.get("on", False))
                        elif command_type == "set_session_automation_record":
                            result = self._set_session_automation_record(params.get("on", False))
                        elif command_type == "re_enable_automation":
                            result = self._re_enable_automation()
                        elif command_type == "set_count_in_duration":
                            result = self._set_count_in_duration(params.get("bars", 0))
                        elif command_type == "set_exclusive_arm":
                            result = self._set_exclusive_arm(params.get("on", False))
                        elif command_type == "set_punch":
                            result = self._set_punch(params.get("punch_in"), params.get("punch_out"))
                        elif command_type == "set_song_scale":
                            result = self._set_song_scale(params.get("scale_name"), params.get("root_note"))
                        elif command_type == "set_track_color":
                            result = self._set_track_color(params.get("track_index", 0),
                                                           params.get("color_index"), params.get("color"))
                        elif command_type == "set_scene_color":
                            result = self._set_scene_color(params.get("scene_index", 0),
                                                           params.get("color_index"), params.get("color"))
                        elif command_type == "duplicate_scene":
                            result = self._duplicate_scene(params.get("index", 0))
                        elif command_type == "set_scene_tempo":
                            result = self._set_scene_tempo(params.get("scene_index", 0), params.get("tempo"))
                        elif command_type == "set_scene_signature":
                            result = self._set_scene_signature(params.get("scene_index", 0),
                                                               params.get("numerator", 4), params.get("denominator", 4))
                        elif command_type == "set_cue_volume":
                            result = self._set_cue_volume(params.get("value", 0.0))

                        # Put the result in the queue
                        response_queue.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message("Error in main thread task: " + str(e))
                        self.log_message(traceback.format_exc())
                        response_queue.put({"status": "error", "message": str(e)})
                
                # Schedule the task to run on the main thread
                try:
                    self.schedule_message(0, main_thread_task)
                except AssertionError:
                    # If we're already on the main thread, execute directly
                    main_thread_task()
                
                # Wait for the response with a timeout
                try:
                    cmd_timeout = 300.0 if command_type == "record_arrangement" else 10.0
                    task_response = response_queue.get(timeout=cmd_timeout)
                    if task_response.get("status") == "error":
                        response["status"] = "error"
                        response["message"] = task_response.get("message", "Unknown error")
                    else:
                        response["result"] = task_response.get("result", {})
                except queue.Empty:
                    response["status"] = "error"
                    response["message"] = "Timeout waiting for operation to complete"
            elif command_type == "get_browser_item":
                uri = params.get("uri", None)
                path = params.get("path", None)
                response["result"] = self._get_browser_item(uri, path)
            elif command_type == "get_browser_categories":
                category_type = params.get("category_type", "all")
                response["result"] = self._get_browser_categories(category_type)
            elif command_type == "get_browser_items":
                path = params.get("path", "")
                item_type = params.get("item_type", "all")
                response["result"] = self._get_browser_items(path, item_type)
            # Add the new browser commands
            elif command_type == "get_browser_tree":
                category_type = params.get("category_type", "all")
                response["result"] = self.get_browser_tree(category_type)
            elif command_type == "get_browser_items_at_path":
                path = params.get("path", "")
                response["result"] = self.get_browser_items_at_path(path)
            else:
                response["status"] = "error"
                response["message"] = "Unknown command: " + command_type
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)
        
        return response
    
    # Command implementations
    
    def _get_session_info(self):
        """Get information about the current session"""
        try:
            result = {
                "tempo": self._song.tempo,
                "signature_numerator": self._song.signature_numerator,
                "signature_denominator": self._song.signature_denominator,
                "track_count": len(self._song.tracks),
                "return_track_count": len(self._song.return_tracks),
                "master_track": {
                    "name": "Master",
                    "volume": self._song.master_track.mixer_device.volume.value,
                    "panning": self._song.master_track.mixer_device.panning.value
                }
            }
            return result
        except Exception as e:
            self.log_message("Error getting session info: " + str(e))
            raise
    
    def _safe_getattr(self, obj, name, default=None):
        """Read a Live API property without letting unsupported properties abort a query."""
        try:
            return getattr(obj, name)
        except Exception:
            return default

    def _get_track_info(self, track_index):
        """Get safe, useful information about regular, group, return, or master tracks."""
        try:
            track = self._get_track(track_index)
            children = None

            if track_index == -1:
                track_kind = "master"
            elif track_index < -1:
                track_kind = "return"
            else:
                is_foldable = self._safe_getattr(track, "is_foldable", None)
                children = self._safe_getattr(track, "children", None)
                explicit_group = self._safe_getattr(track, "is_group_track", None)
                if explicit_group is None:
                    explicit_group = is_foldable is True or children is not None
                track_kind = "group" if explicit_group else "regular"

            raw_clip_slots = self._safe_getattr(track, "clip_slots", [])
            try:
                clip_slots_source = list(raw_clip_slots) if raw_clip_slots is not None else []
            except Exception:
                clip_slots_source = []
            clip_slots = []
            for slot_index, slot in enumerate(clip_slots_source):
                has_clip = bool(self._safe_getattr(slot, "has_clip", False))
                clip_info = None
                if has_clip:
                    clip = self._safe_getattr(slot, "clip", None)
                    if clip is not None:
                        clip_info = {
                            "name": self._safe_getattr(clip, "name", ""),
                            "length": self._safe_getattr(clip, "length", 0),
                            "is_playing": self._safe_getattr(clip, "is_playing", False),
                            "is_recording": self._safe_getattr(clip, "is_recording", False)
                        }

                clip_slots.append({
                    "index": slot_index,
                    "has_clip": has_clip,
                    "clip": clip_info
                })

            raw_devices = self._safe_getattr(track, "devices", [])
            try:
                devices_source = list(raw_devices) if raw_devices is not None else []
            except Exception:
                devices_source = []
            devices = []
            for device_index, device in enumerate(devices_source):
                devices.append({
                    "index": device_index,
                    "name": self._safe_getattr(device, "name", ""),
                    "class_name": self._safe_getattr(device, "class_name", ""),
                    "type": self._get_device_type(device)
                })

            mixer_device = self._safe_getattr(track, "mixer_device", None)
            volume_parameter = self._safe_getattr(mixer_device, "volume", None)
            panning_parameter = self._safe_getattr(mixer_device, "panning", None)
            volume = self._safe_getattr(volume_parameter, "value", None)
            panning = self._safe_getattr(panning_parameter, "value", None)

            result = {
                "index": track_index,
                "name": self._safe_getattr(track, "name", ""),
                "kind": track_kind,
                "track_kind": track_kind,
                "is_audio_track": bool(self._safe_getattr(track, "has_audio_input", False)),
                "is_midi_track": bool(self._safe_getattr(track, "has_midi_input", False)),
                "mute": bool(self._safe_getattr(track, "mute", False)),
                "solo": bool(self._safe_getattr(track, "solo", False)),
                "volume": volume,
                "panning": panning,
                "output_meter_level": self._safe_getattr(track, "output_meter_level", None),
                "clip_slots": clip_slots,
                "devices": devices
            }

            # Group properties differ across Live versions, so expose only values
            # that can be read safely and keep all values JSON serializable.
            arm = self._safe_getattr(track, "arm", None)
            if arm is not None:
                result["arm"] = bool(arm)
            is_foldable = self._safe_getattr(track, "is_foldable", None)
            if is_foldable is not None:
                result["is_foldable"] = bool(is_foldable)
            is_grouped = self._safe_getattr(track, "is_grouped", None)
            fold_state = self._safe_getattr(track, "fold_state", None)
            group_track = self._safe_getattr(track, "group_track", None)
            group_track_name = self._safe_getattr(group_track, "name", None) if group_track is not None else None
            group_track_index = None
            if group_track is not None:
                try:
                    for candidate_index, candidate in enumerate(self._song.tracks):
                        if candidate is group_track:
                            group_track_index = candidate_index
                            break
                except Exception:
                    pass
            child_count = None
            if children is not None:
                try:
                    child_count = len(children)
                except Exception:
                    pass

            result["is_group_track"] = track_kind == "group"
            if is_grouped is not None:
                result["is_grouped"] = bool(is_grouped)
            if fold_state is not None:
                result["fold_state"] = fold_state
            if group_track_name is not None:
                result["group_track_name"] = group_track_name
            if group_track_index is not None:
                result["group_track_index"] = group_track_index
            if child_count is not None:
                result["child_track_count"] = child_count
            return result
        except Exception as e:
            self.log_message("Error getting track info: " + str(e))
            raise
    
    def _set_track_monitoring(self, track_index, state):
        """Set track monitoring state (0=In, 1=Auto, 2=Off)"""
        try:
            track = self._get_track(track_index)
            track.current_monitoring_state = state
            return {"monitoring_state": track.current_monitoring_state}
        except Exception as e:
            self.log_message("Error setting track monitoring: " + str(e))
            raise

    def _get_track_routing(self, track_index):
        """Get input/output routing info for a track"""
        try:
            track = self._get_track(track_index)
            result = {
                "input_routing_type": str(track.input_routing_type.display_name) if hasattr(track.input_routing_type, 'display_name') else str(track.input_routing_type),
                "output_routing_type": str(track.output_routing_type.display_name) if hasattr(track.output_routing_type, 'display_name') else str(track.output_routing_type),
            }
            try:
                ch = getattr(track, "input_routing_channel", None)
                result["input_routing_channel"] = str(ch.display_name) if ch is not None else None
                result["available_input_routing_channels"] = [str(c.display_name) for c in track.available_input_routing_channels]
            except Exception:
                pass
            if hasattr(track, 'available_input_routing_types'):
                result["available_input_routing_types"] = [
                    {"display_name": str(r.display_name) if hasattr(r, 'display_name') else str(r)}
                    for r in track.available_input_routing_types
                ]
            if hasattr(track, 'available_output_routing_types'):
                result["available_output_routing_types"] = [
                    {"display_name": str(r.display_name) if hasattr(r, 'display_name') else str(r)}
                    for r in track.available_output_routing_types
                ]
            return result
        except Exception as e:
            self.log_message("Error getting track routing: " + str(e))
            raise

    def _set_track_input_routing(self, track_index, routing_type_name, channel_name=None):
        """Set track input routing by name; `channel_name` picks the channel ("Ch. 5", "1/2",
        "Post FX"), otherwise the type's first channel."""
        try:
            track = self._get_track(track_index)
            for routing_type in track.available_input_routing_types:
                name = str(routing_type.display_name) if hasattr(routing_type, 'display_name') else str(routing_type)
                if name == routing_type_name:
                    track.input_routing_type = routing_type
                    # the channel is a separate property and can stay pointed at the previous
                    # type's channel (recording then captures silence); pick the new type's first
                    chosen = None
                    try:
                        channels = list(track.available_input_routing_channels)
                        pick = channels[0] if channels else None
                        if channel_name:
                            want = str(channel_name).lower()
                            for c in channels:
                                if str(c.display_name).lower() == want:
                                    pick = c
                                    break
                            else:
                                raise Exception("no input channel %r; available: %s" % (
                                    channel_name, ", ".join(str(c.display_name) for c in channels)))
                        if pick is not None:
                            track.input_routing_channel = pick
                            chosen = str(pick.display_name)
                    except Exception as ce:
                        if channel_name:
                            raise
                        self.log_message("input channel not set: " + str(ce))
                    return {"input_routing_type": routing_type_name, "input_routing_channel": chosen}
            raise Exception("Routing type not found: " + routing_type_name)
        except Exception as e:
            self.log_message("Error setting track input routing: " + str(e))
            raise

    def _set_track_output_routing(self, track_index, routing_type_name):
        """Set track output routing by name"""
        try:
            track = self._get_track(track_index)
            available = []
            for routing_type in track.available_output_routing_types:
                name = str(routing_type.display_name) if hasattr(routing_type, 'display_name') else str(routing_type)
                available.append(name)
                if name.lower() == routing_type_name.lower():
                    track.output_routing_type = routing_type
                    return {"output_routing_type": name}
            raise Exception("Routing type not found: " + routing_type_name + ". Available: " + ", ".join(available))
        except Exception as e:
            self.log_message("Error setting track output routing: " + str(e))
            raise

    def _get_track(self, track_index):
        """Get a track by index. Use -1 for master track, -2/-3/etc for return tracks."""
        if track_index == -1:
            return self._song.master_track
        elif track_index < -1:
            return_index = -(track_index + 2)  # -2 -> 0, -3 -> 1
            if return_index < 0 or return_index >= len(self._song.return_tracks):
                raise IndexError("Return track index out of range")
            return self._song.return_tracks[return_index]
        else:
            if track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            return self._song.tracks[track_index]

    def _set_track_volume(self, track_index, volume):
        """Set a track's volume using a normalized value (0.0 to 1.0)"""
        try:
            track = self._get_track(track_index)
            if volume < 0.0 or volume > 1.0:
                raise ValueError("Volume must be between 0.0 and 1.0")
            vol_param = track.mixer_device.volume
            actual_value = vol_param.min + volume * (vol_param.max - vol_param.min)
            vol_param.value = actual_value
            return {
                "track_name": track.name,
                "volume": vol_param.value,
                "normalized_volume": volume
            }
        except Exception as e:
            self.log_message("Error setting track volume: " + str(e))
            raise

    def _set_track_panning(self, track_index, panning):
        """Set a track's panning using a normalized value (0.0 to 1.0, 0.5 = center)"""
        try:
            track = self._get_track(track_index)
            if panning < 0.0 or panning > 1.0:
                raise ValueError("Panning must be between 0.0 and 1.0")
            pan_param = track.mixer_device.panning
            actual_value = pan_param.min + panning * (pan_param.max - pan_param.min)
            pan_param.value = actual_value
            return {
                "track_name": track.name,
                "panning": pan_param.value,
                "normalized_panning": panning
            }
        except Exception as e:
            self.log_message("Error setting track panning: " + str(e))
            raise

    def _get_arrangement_info(self):
        """Get current arrangement state"""
        try:
            return {
                "current_song_time": self._song.current_song_time,
                "is_playing": self._song.is_playing,
                "record_mode": self._song.record_mode,
                "arrangement_overdub": self._song.arrangement_overdub,
                "back_to_arranger": self._song.back_to_arranger,
                "loop": self._song.loop,
                "loop_start": self._song.loop_start,
                "loop_length": self._song.loop_length,
                "tempo": self._song.tempo,
                "scene_count": len(self._song.scenes),
                "song_length": self._song.song_length
            }
        except Exception as e:
            self.log_message("Error getting arrangement info: " + str(e))
            raise

    def _fire_scene(self, scene_index):
        """Fire all clips in a scene"""
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range (0-{0})".format(len(self._song.scenes) - 1))
            scene = self._song.scenes[scene_index]
            scene.fire()
            return {
                "scene_index": scene_index,
                "scene_name": scene.name,
                "fired": True
            }
        except Exception as e:
            self.log_message("Error firing scene: " + str(e))
            raise

    def _set_song_time(self, time):
        """Set the current song time (arrangement position) in beats.
        Retries up to 5 times if the position doesn't land correctly."""
        try:
            target = max(0.0, time)
            for attempt in range(5):
                self._song.current_song_time = target
                actual = self._song.current_song_time
                if abs(actual - target) < 0.5:
                    break
                self.log_message("set_song_time attempt {0}: wanted {1}, got {2}".format(
                    attempt + 1, target, actual))
            return {
                "current_song_time": self._song.current_song_time
            }
        except Exception as e:
            self.log_message("Error setting song time: " + str(e))
            raise

    def _set_record_mode(self, on):
        """Enable or disable arrangement recording"""
        try:
            self._song.record_mode = 1 if on else 0
            return {
                "record_mode": self._song.record_mode
            }
        except Exception as e:
            self.log_message("Error setting record mode: " + str(e))
            raise

    def _capture_midi(self, destination):
        """Capture MIDI into Live's selected destination: 0=auto, 1=session, 2=arrangement."""
        try:
            if isinstance(destination, bool) or not isinstance(destination, _INTEGER_TYPES):
                raise ValueError("destination must be an integer 0, 1, or 2")
            if destination not in (0, 1, 2):
                raise ValueError("destination must be 0 (auto), 1 (session), or 2 (arrangement)")

            destination_name = ("auto", "session", "arrangement")[destination]
            self._song.capture_midi(destination)
            return {
                "captured": True,
                "destination": destination,
                "destination_name": destination_name
            }
        except Exception as e:
            self.log_message("Error capturing MIDI: " + str(e))
            raise

    def _set_arrangement_overdub(self, on):
        """Enable or disable arrangement overdub"""
        try:
            self._song.arrangement_overdub = 1 if on else 0
            return {
                "arrangement_overdub": self._song.arrangement_overdub
            }
        except Exception as e:
            self.log_message("Error setting arrangement overdub: " + str(e))
            raise

    def _set_back_to_arranger(self, value=False):
        """Song.back_to_arranger is True while session clips override the arrangement (the
        'Back to Arrangement' button is lit). Setting it False is what clicking that button
        does: the arrangement plays again. Default False; pass True to hand control to session."""
        try:
            self._song.back_to_arranger = bool(value)
            return {
                "back_to_arranger": self._song.back_to_arranger
            }
        except Exception as e:
            self.log_message("Error setting back to arranger: " + str(e))
            raise

    def _set_arrangement_loop(self, on, start, length):
        """Set arrangement loop on/off, start position and length in beats"""
        try:
            self._song.loop = on
            if start is not None:
                self._song.loop_start = max(0.0, start)
            if length is not None:
                self._song.loop_length = max(0.0, length)
            return {
                "loop": self._song.loop,
                "loop_start": self._song.loop_start,
                "loop_length": self._song.loop_length
            }
        except Exception as e:
            self.log_message("Error setting arrangement loop: " + str(e))
            raise

    def _set_track_mute(self, track_index, mute):
        """Mute or unmute a track"""
        try:
            track = self._get_track(track_index)
            track.mute = mute
            return {
                "track_name": track.name,
                "mute": track.mute
            }
        except Exception as e:
            self.log_message("Error setting track mute: " + str(e))
            raise

    def _set_track_solo(self, track_index, solo):
        """Solo or unsolo a track"""
        try:
            track = self._get_track(track_index)
            track.solo = solo
            return {
                "track_name": track.name,
                "solo": track.solo
            }
        except Exception as e:
            self.log_message("Error setting track solo: " + str(e))
            raise

    def _delete_clip(self, track_index, clip_index):
        """Delete a clip from a clip slot"""
        try:
            track = self._get_track(track_index)
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            clip_slot = track.clip_slots[clip_index]
            if not clip_slot.has_clip:
                raise ValueError("No clip in slot {0}".format(clip_index))
            clip_slot.delete_clip()
            return {
                "track_name": track.name,
                "clip_index": clip_index,
                "deleted": True
            }
        except Exception as e:
            self.log_message("Error deleting clip: " + str(e))
            raise

    def _duplicate_clip(self, track_index, clip_index, target_index):
        """Duplicate a clip to another slot"""
        try:
            track = self._get_track(track_index)
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Source clip index out of range")
            if not track.clip_slots[clip_index].has_clip:
                raise ValueError("No clip in source slot {0}".format(clip_index))
            if target_index < 0:
                # Find next empty slot
                target_index = -1
                for i in range(len(track.clip_slots)):
                    if not track.clip_slots[i].has_clip:
                        target_index = i
                        break
                if target_index < 0:
                    raise ValueError("No empty clip slots available")
            if target_index >= len(track.clip_slots):
                raise IndexError("Target clip index out of range")
            if track.clip_slots[target_index].has_clip:
                raise ValueError("Target slot {0} already has a clip".format(target_index))
            track.clip_slots[clip_index].duplicate_clip_to(track.clip_slots[target_index])
            return {
                "track_name": track.name,
                "source_index": clip_index,
                "target_index": target_index,
                "duplicated": True
            }
        except Exception as e:
            self.log_message("Error duplicating clip: " + str(e))
            raise

    def _duplicate_clip_to_arrangement(self, track_index, clip_index, destination_time):
        """Duplicate a session clip into the arrangement on the same track."""
        try:
            track = self._get_track(track_index)
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Source clip index out of range")
            slot = track.clip_slots[clip_index]
            if not slot.has_clip:
                raise ValueError("No clip in source slot {0}".format(clip_index))
            if not hasattr(track, "duplicate_clip_to_arrangement"):
                raise Exception(
                    "duplicate_clip_to_arrangement requires Live 12.3+"
                )
            if destination_time is None:
                raise ValueError("destination_time is required")
            destination_time = float(destination_time)
            if destination_time < 0.0:
                raise ValueError("destination_time must be non-negative")
            track.duplicate_clip_to_arrangement(slot.clip, destination_time)
            return {
                "duplicated": True,
                "track_index": track_index,
                "track_name": self._safe_getattr(track, "name", ""),
                "source_clip_index": clip_index,
                "destination_time": destination_time,
                "arrangement_clip_count": len(self._get_arrangement_clips_safe(track))
            }
        except Exception as e:
            self.log_message("Error duplicating clip to arrangement: " + str(e))
            raise

    def _insert_device(self, track_index, device_name, target_index=None):
        """Insert a native Live device using Track.insert_device (Live 12.3+)."""
        try:
            track = self._get_track(track_index)
            if not isinstance(device_name, _STRING_TYPES) or not device_name.strip():
                raise ValueError("device_name is required")
            if not hasattr(track, "insert_device"):
                raise Exception(
                    "insert_device requires Live 12.3+ and supports native Live devices only; "
                    "use browser/.adg workflows for VST/AU and Max devices"
                )
            if target_index is not None:
                target_index = self._integer_value(target_index, "target_index")
                if target_index < 0 or target_index > len(track.devices):
                    raise IndexError("Target device index out of range")
                track.insert_device(device_name, target_index)
            else:
                track.insert_device(device_name)
            devices = list(track.devices)
            inserted_index = target_index if target_index is not None else len(devices) - 1
            inserted = devices[inserted_index] if 0 <= inserted_index < len(devices) else None
            return {
                "inserted": True,
                "track_index": track_index,
                "track_name": self._safe_getattr(track, "name", ""),
                "device_index": inserted_index,
                "device_name": self._safe_getattr(inserted, "name", device_name),
                "device_count": len(devices)
            }
        except Exception as e:
            self.log_message("Error inserting device: " + str(e))
            raise

    def _create_scene(self, index):
        """Create a new scene at the specified index"""
        try:
            if index < 0:
                index = len(self._song.scenes)
            scene = self._song.create_scene(index)
            return {
                "scene_index": index,
                "scene_count": len(self._song.scenes)
            }
        except Exception as e:
            self.log_message("Error creating scene: " + str(e))
            raise

    def _set_scene_name(self, scene_index, name):
        """Set a scene's name"""
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            self._song.scenes[scene_index].name = name
            return {
                "scene_index": scene_index,
                "name": self._song.scenes[scene_index].name
            }
        except Exception as e:
            self.log_message("Error setting scene name: " + str(e))
            raise

    def _create_audio_track(self, index):
        """Create a new audio track at the specified index"""
        try:
            if index < 0:
                index = len(self._song.tracks)
            self._song.create_audio_track(index)
            track = self._song.tracks[index]
            return {
                "index": index,
                "name": track.name,
                "track_count": len(self._song.tracks)
            }
        except Exception as e:
            self.log_message("Error creating audio track: " + str(e))
            raise

    def _delete_track(self, track_index):
        """Delete a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track_name = self._song.tracks[track_index].name
            self._song.delete_track(track_index)
            return {
                "deleted_track": track_name,
                "track_count": len(self._song.tracks)
            }
        except Exception as e:
            self.log_message("Error deleting track: " + str(e))
            raise

    def _get_arrangement_clips_safe(self, track):
        """Return arrangement clips, treating unsupported Live track APIs as empty."""
        try:
            clips = getattr(track, "arrangement_clips", None)
            return list(clips) if clips is not None else []
        except Exception:
            return []

    def _arrangement_clip_info(self, clip):
        """JSON-safe arrangement clip fields; skip properties Live cannot read."""
        is_audio = bool(self._safe_getattr(clip, "is_audio_clip", False))
        clip_info = {
            "name": self._safe_getattr(clip, "name", ""),
            "start_time": self._safe_getattr(clip, "start_time", 0),
            "end_time": self._safe_getattr(clip, "end_time", 0),
            "length": self._safe_getattr(clip, "length", 0),
            "is_midi_clip": bool(self._safe_getattr(clip, "is_midi_clip", False)),
            "is_audio_clip": is_audio,
        }
        if is_audio:
            file_path = self._safe_getattr(clip, "file_path", None)
            if file_path is not None:
                clip_info["file_path"] = file_path
        return clip_info

    def _get_arrangement_clips(self, track_index):
        """Get arrangement clips for a track"""
        try:
            track = self._get_track(track_index)
            clips = [self._arrangement_clip_info(clip)
                     for clip in self._get_arrangement_clips_safe(track)]
            return {
                "track_index": track_index,
                "track_name": self._safe_getattr(track, "name", ""),
                "arrangement_clip_count": len(clips),
                "clips": clips
            }
        except Exception as e:
            self.log_message("Error getting arrangement clips: " + str(e))
            raise

    def _get_full_arrangement(self):
        """Get arrangement clips for all tracks at once"""
        try:
            tracks_data = []
            all_tracks = list(self._song.tracks)
            for i, track in enumerate(all_tracks):
                clips = [self._arrangement_clip_info(clip)
                         for clip in self._get_arrangement_clips_safe(track)]
                if clips:
                    tracks_data.append({
                        "track_index": i,
                        "track_name": self._safe_getattr(track, "name", ""),
                        "clips": clips
                    })

            # Scene info
            scenes = []
            for i, scene in enumerate(self._song.scenes):
                scenes.append({"index": i, "name": self._safe_getattr(scene, "name", "")})

            tempo = self._safe_getattr(self._song, "tempo", 0)
            sig_num = self._safe_getattr(self._song, "signature_numerator", 4)
            sig_den = self._safe_getattr(self._song, "signature_denominator", 4)
            return {
                "tempo": tempo,
                "time_signature": "{0}/{1}".format(sig_num, sig_den),
                "song_length": self._safe_getattr(self._song, "song_length", 0),
                "tracks_with_clips": tracks_data,
                "scenes": scenes
            }
        except Exception as e:
            self.log_message("Error getting full arrangement: " + str(e))
            raise

    def _delete_scene(self, scene_index):
        """Delete a scene"""
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene_name = self._song.scenes[scene_index].name
            self._song.delete_scene(scene_index)
            return {
                "deleted_scene": scene_name,
                "scene_count": len(self._song.scenes)
            }
        except Exception as e:
            self.log_message("Error deleting scene: " + str(e))
            raise

    def _record_arrangement(self, sections, start_time=0.0):
        """Record session clips into arrangement by firing scenes at timed intervals.
        sections: list of {"scene_index": int, "bars": int}
        start_time: arrangement position (in beats) to begin recording from. Default 0.

        Uses polling with fire-and-forget scene fires (no round-trip wait).
        clip_trigger_quantization=4 (1 Bar) snaps fires to bar boundaries.
        Fires scene 2 beats before target so quantization lands on the right bar."""
        import time as time_module

        tempo = self._song.tempo
        beats_per_bar = self._song.signature_numerator
        seconds_per_beat = 60.0 / tempo

        result_holder = {"result": None, "error": None, "done": False}
        saved_quantization = [0]
        cancelled = [False]

        def do_on_main(fn):
            """Execute fn on main thread and wait for completion."""
            done_event = threading.Event()
            error_holder = [None]
            def task():
                try:
                    fn()
                except Exception as e:
                    error_holder[0] = e
                done_event.set()
            self.schedule_message(0, task)
            done_event.wait(timeout=5.0)
            if error_holder[0]:
                raise error_holder[0]

        def fire_and_forget(fn):
            """Schedule fn on main thread without waiting. For time-critical fires."""
            def guarded():
                if not cancelled[0]:
                    fn()
            self.schedule_message(0, guarded)

        def recording_thread():
            try:
                # Save and set clip trigger quantization to 1 Bar
                def set_quantization():
                    saved_quantization[0] = self._song.clip_trigger_quantization
                    self._song.clip_trigger_quantization = 4  # 1 Bar
                do_on_main(set_quantization)

                # Disarm all tracks to prevent stray MIDI recording
                def disarm_all():
                    for track in self._song.tracks:
                        if track.can_be_armed and track.arm:
                            track.arm = False
                do_on_main(disarm_all)

                # Stop playback and prepare
                do_on_main(lambda: self._song.stop_playing() if self._song.is_playing else None)
                time_module.sleep(0.1)
                do_on_main(lambda: setattr(self._song, 'back_to_arranger', True))
                time_module.sleep(0.05)

                # Seek to start_time
                def seek_start():
                    self._song.current_song_time = start_time
                    for _ in range(5):
                        if abs(self._song.current_song_time - start_time) < 0.5:
                            break
                        self._song.current_song_time = start_time
                do_on_main(seek_start)
                time_module.sleep(0.05)

                # Enable recording
                do_on_main(lambda: setattr(self._song, 'record_mode', 1))
                time_module.sleep(0.05)

                total_bars = 0
                recorded_sections = []
                scene_count = len(self._song.scenes)

                for i, section in enumerate(sections):
                    si = section.get("scene_index", 0)
                    bars = section.get("bars", 8)

                    if si < 0 or si >= scene_count:
                        self.log_message("Skipping invalid scene index: {0}".format(si))
                        continue

                    # Fire this scene
                    scene_name = [""]
                    if i == 0:
                        # First scene: fire immediately
                        def fire_first(idx=si):
                            self._song.scenes[idx].fire()
                            scene_name[0] = self._song.scenes[idx].name
                        do_on_main(fire_first)
                    else:
                        # Already fired by previous iteration, just get name
                        def get_name(idx=si):
                            scene_name[0] = self._song.scenes[idx].name
                        do_on_main(get_name)

                    self.log_message("Recording section {0}: scene {1} ({2}) for {3} bars".format(
                        i + 1, si, scene_name[0], bars))

                    target_beat = start_time + (total_bars + bars) * beats_per_bar
                    next_section = sections[i + 1] if i + 1 < len(sections) else None
                    next_fired = [False]

                    # Fire next scene 2 beats before target.
                    # With 1-bar quantization, this is within the last bar before
                    # the target boundary, so it snaps to the target beat.
                    # Use fire_and_forget (no round-trip wait) to minimize latency.
                    fire_beat = target_beat - 2.0 if next_section else None

                    while True:
                        # Read current time — need do_on_main for this
                        current_holder = [0.0]
                        def get_time():
                            current_holder[0] = self._song.current_song_time
                        do_on_main(get_time)
                        current = current_holder[0]

                        # Fire next scene (fire-and-forget, no waiting)
                        if fire_beat is not None and not next_fired[0] and current >= fire_beat:
                            next_si = next_section.get("scene_index", 0)
                            def fire_next(idx=next_si):
                                self._song.scenes[idx].fire()
                            fire_and_forget(fire_next)
                            next_fired[0] = True
                            self.log_message("Fired next scene {0} at beat {1:.1f} (target {2})".format(
                                next_si, current, target_beat))

                        if current >= target_beat - 0.5:
                            break

                        remaining_seconds = (target_beat - current) * seconds_per_beat
                        if remaining_seconds > 2.0:
                            time_module.sleep(remaining_seconds - 1.5)
                        else:
                            time_module.sleep(0.02)

                    recorded_sections.append({
                        "scene_index": si,
                        "scene_name": scene_name[0],
                        "bars": bars,
                        "start_bar": total_bars + 1,
                        "end_bar": total_bars + bars
                    })
                    total_bars += bars

                # Stop recording
                do_on_main(lambda: setattr(self._song, 'record_mode', 0))
                time_module.sleep(0.05)
                do_on_main(lambda: self._song.stop_playing())
                time_module.sleep(0.1)

                # Restore quantization and return to arrangement
                def cleanup():
                    self._song.clip_trigger_quantization = saved_quantization[0]
                    self._song.stop_all_clips()
                    self._song.back_to_arranger = True
                    self._song.current_song_time = 0.0
                do_on_main(cleanup)

                result_holder["result"] = {
                    "total_bars": total_bars,
                    "total_beats": total_bars * beats_per_bar,
                    "sections": recorded_sections,
                    "tempo": tempo
                }
            except Exception as e:
                cancelled[0] = True
                try:
                    do_on_main(lambda: setattr(self._song, 'record_mode', 0))
                    do_on_main(lambda: self._song.stop_playing())
                    do_on_main(lambda: setattr(self._song, 'clip_trigger_quantization', saved_quantization[0]))
                except:
                    pass
                self.log_message("Error recording arrangement: " + str(e))
                result_holder["error"] = e
            finally:
                result_holder["done"] = True

        rec_thread = threading.Thread(target=recording_thread)
        rec_thread.daemon = True
        rec_thread.start()

        total_duration = sum(s.get("bars", 8) for s in sections) * beats_per_bar * seconds_per_beat
        rec_thread.join(timeout=total_duration + 30)

        if result_holder["error"]:
            raise result_holder["error"]
        if not result_holder["done"]:
            raise Exception("Recording timed out")
        return result_holder["result"]

    def _delete_device(self, track_index, device_index):
        """Delete a device from a track"""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device_name = track.devices[device_index].name
            track.delete_device(device_index)
            return {
                "deleted_device": device_name,
                "device_count": len(track.devices)
            }
        except Exception as e:
            self.log_message("Error deleting device: " + str(e))
            raise

    def _duplicate_track(self, track_index):
        """Duplicate a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track_name = self._song.tracks[track_index].name
            self._song.duplicate_track(track_index)
            new_track = self._song.tracks[track_index + 1]
            return {
                "original_track": track_name,
                "new_track_index": track_index + 1,
                "new_track_name": new_track.name,
                "track_count": len(self._song.tracks)
            }
        except Exception as e:
            self.log_message("Error duplicating track: " + str(e))
            raise

    def _set_clip_loop(self, track_index, clip_index, loop_start, loop_end, looping):
        """Set clip loop settings"""
        try:
            track = self._song.tracks[track_index]
            clip_slot = track.clip_slots[clip_index]
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            if looping is not None:
                clip.looping = bool(looping)
            if loop_start is not None:
                clip.loop_start = float(loop_start)
            if loop_end is not None:
                clip.loop_end = float(loop_end)
            return {
                "looping": clip.looping,
                "loop_start": clip.loop_start,
                "loop_end": clip.loop_end,
                "length": clip.length
            }
        except Exception as e:
            self.log_message("Error setting clip loop: " + str(e))
            raise

    def _note_dict(self, note):
        """Return the fields Live exposes for a Note, including its stable note_id."""
        result = {
            "note_id": self._safe_getattr(note, "note_id", None),
            "pitch": self._safe_getattr(note, "pitch", None),
            "start_time": self._safe_getattr(note, "start_time", None),
            "duration": self._safe_getattr(note, "duration", None),
            "velocity": self._safe_getattr(note, "velocity", None),
            "mute": self._safe_getattr(note, "mute", False)
        }
        for name in ("probability", "velocity_deviation", "release_velocity"):
            value = self._safe_getattr(note, name, None)
            if value is not None:
                result[name] = value
        return result

    def _clip_note_dicts(self, clip):
        if not hasattr(clip, "get_notes_extended"):
            raise Exception("get_notes_extended is required for note IDs")
        notes = clip.get_notes_extended(from_pitch=0, pitch_span=128,
                                        from_time=0, time_span=clip.length)
        return [self._note_dict(note) for note in notes]

    def _get_clip_notes(self, track_index, clip_index):
        """Get all notes from a MIDI clip."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=True)
            note_list = self._clip_note_dicts(clip)
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "clip_name": clip.name,
                "length": clip.length,
                "note_count": len(note_list),
                "notes": note_list
            }
        except Exception as e:
            self.log_message("Error getting clip notes: " + str(e))
            raise

    def _get_arrangement_clip_notes(self, track_index, arrangement_clip_index):
        """Get all notes from a MIDI clip in the arrangement view (by index in track.arrangement_clips)."""
        try:
            track = self._get_track(track_index)
            clips = self._get_arrangement_clips_safe(track)
            if arrangement_clip_index < 0 or arrangement_clip_index >= len(clips):
                raise IndexError("Arrangement clip index out of range")
            clip = clips[arrangement_clip_index]
            if not clip.is_midi_clip:
                raise Exception("Not a MIDI clip")
            note_list = self._clip_note_dicts(clip)
            return {
                "track_index": track_index,
                "arrangement_clip_index": arrangement_clip_index,
                "clip_name": clip.name,
                "start_time": float(clip.start_time) if hasattr(clip, 'start_time') else 0,
                "length": clip.length,
                "note_count": len(note_list),
                "notes": note_list,
            }
        except Exception as e:
            self.log_message("Error getting arrangement clip notes: " + str(e))
            raise

    def _apply_note_modifications(self, track_index, clip_index, notes, arrangement_clip_index=None):
        """Merge note patches by note_id and apply them to a session or arrangement clip."""
        try:
            if not isinstance(notes, (list, tuple)):
                raise ValueError("notes must be a list of note dictionaries")
            clip = self._session_clip(track_index, clip_index, midi=True,
                                      arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "apply_note_modifications"):
                raise Exception("apply_note_modifications requires Live 12.3+")
            current = self._clip_note_dicts(clip)
            by_id = {}
            for note in current:
                note_id = note.get("note_id")
                if note_id is not None:
                    by_id[note_id] = note
            full_notes = []
            for patch in notes:
                if not isinstance(patch, dict):
                    raise ValueError("each note modification must be a dictionary")
                if "note_id" not in patch or patch.get("note_id") is None:
                    raise ValueError("each note modification must include note_id")
                note_id = patch.get("note_id")
                if note_id not in by_id:
                    raise ValueError("note_id {0} was not found in the clip".format(note_id))
                merged = dict(by_id[note_id])
                merged.update(patch)
                full_notes.append(merged)
            clip.apply_note_modifications({"notes": full_notes})
            result = {
                "track_index": track_index,
                "clip_index": clip_index,
                "modified_count": len(full_notes),
                "notes": full_notes
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error applying note modifications: " + str(e))
            raise

    def _delete_arrangement_clip(self, track_index, arrangement_clip_index):
        """Delete an arrangement clip by track + index in track.arrangement_clips."""
        try:
            track = self._song.tracks[track_index]
            if not hasattr(track, 'arrangement_clips'):
                raise Exception("Track has no arrangement_clips")
            clips = list(track.arrangement_clips)
            if arrangement_clip_index < 0 or arrangement_clip_index >= len(clips):
                raise IndexError("Arrangement clip index out of range")
            clip = clips[arrangement_clip_index]
            start = float(clip.start_time) if hasattr(clip, 'start_time') else 0.0
            end = float(clip.end_time) if hasattr(clip, 'end_time') else start + clip.length
            # Live exposes Track.delete_clip(clip) on most versions; fall back to time range.
            if hasattr(track, 'delete_clip'):
                track.delete_clip(clip)
            elif hasattr(self._song, 'delete_arrangement_clip'):
                self._song.delete_arrangement_clip(track, start, end)
            else:
                raise Exception("No delete arrangement clip method available on this Live version")
            return {
                "track_index": track_index,
                "deleted_index": arrangement_clip_index,
                "remaining_count": len(track.arrangement_clips),
            }
        except Exception as e:
            self.log_message("Error deleting arrangement clip: " + str(e))
            raise

    def _set_track_arm(self, track_index, arm):
        """Set track arm state"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            track = self._song.tracks[track_index]
            if not track.can_be_armed:
                raise Exception("Track cannot be armed")
            track.arm = bool(arm)
            return {
                "track_index": track_index,
                "track_name": track.name,
                "arm": track.arm
            }
        except Exception as e:
            self.log_message("Error setting track arm: " + str(e))
            raise

    def _set_send_level(self, track_index, send_index, value):
        """Set send level for a track"""
        try:
            track = self._get_track(track_index)
            sends = track.mixer_device.sends
            if send_index < 0 or send_index >= len(sends):
                raise IndexError("Send index out of range (track has {0} sends)".format(len(sends)))
            send = sends[send_index]
            send.value = max(send.min, min(send.max, send.min + float(value) * (send.max - send.min)))
            return {
                "track_index": track_index,
                "send_index": send_index,
                "value": value,
                "actual_value": send.value
            }
        except Exception as e:
            self.log_message("Error setting send level: " + str(e))
            raise

    def _set_time_signature(self, numerator, denominator):
        """Set the song time signature"""
        try:
            self._song.signature_numerator = int(numerator)
            self._song.signature_denominator = int(denominator)
            return {
                "numerator": self._song.signature_numerator,
                "denominator": self._song.signature_denominator
            }
        except Exception as e:
            self.log_message("Error setting time signature: " + str(e))
            raise

    def _set_metronome(self, on):
        """Set metronome on/off"""
        try:
            self._song.metronome = bool(on)
            return {"metronome": self._song.metronome}
        except Exception as e:
            self.log_message("Error setting metronome: " + str(e))
            raise

    def _set_clip_envelope(self, track_index, clip_index, device_index, parameter_index, points, arrangement_clip_index=None):
        """Set automation envelope points for a parameter in a clip.
        points: list of {"time": float, "value": float} (value is normalized 0-1)"""
        try:
            track = self._get_track(track_index)
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            if self._clip_is_arrangement(clip, arrangement_clip_index):
                raise Exception(_ARRANGEMENT_ENVELOPE_NOTE)

            device = track.devices[device_index]
            param = device.parameters[parameter_index]

            # Try to get existing envelope, or create one
            envelope = clip.automation_envelope(param)
            if envelope is None:
                # Create a new envelope for this parameter
                envelope = clip.create_automation_envelope(param)
            if envelope is None:
                raise Exception("Could not create automation envelope for parameter")

            # Sort points by time and interpolate smooth ramps between them
            sorted_points = sorted(points, key=lambda p: float(p.get("time", 0)))
            step_size = 0.25  # beats per interpolation step
            for i in range(len(sorted_points) - 1):
                t0 = float(sorted_points[i].get("time", 0))
                v0 = float(sorted_points[i].get("value", 0))
                t1 = float(sorted_points[i + 1].get("time", 0))
                v1 = float(sorted_points[i + 1].get("value", 0))
                segment_duration = t1 - t0
                num_steps = max(1, int(segment_duration / step_size))
                for s in range(num_steps):
                    frac = s / float(num_steps)
                    t = t0 + frac * segment_duration
                    v = v0 + frac * (v1 - v0)
                    actual = param.min + v * (param.max - param.min)
                    envelope.insert_step(t, step_size, actual)
            # Last point holds for 1 beat
            if sorted_points:
                last = sorted_points[-1]
                t = float(last.get("time", 0))
                v = float(last.get("value", 0))
                actual = param.min + v * (param.max - param.min)
                envelope.insert_step(t, 1.0, actual)

            result = {
                "track_index": track_index,
                "clip_index": clip_index,
                "device_index": device_index,
                "parameter_index": parameter_index,
                "parameter_name": param.name,
                "points_set": len(points)
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip envelope: " + str(e))
            raise

    def _get_clip_envelope(self, track_index, clip_index, device_index, parameter_index, arrangement_clip_index=None):
        """Read automation envelope data for a parameter in a clip."""
        try:
            track = self._get_track(track_index)
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)

            device = track.devices[device_index]
            param = device.parameters[parameter_index]

            if self._clip_is_arrangement(clip, arrangement_clip_index):
                result = {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "parameter_name": param.name,
                    "has_envelope": False,
                    "points": [],
                    "note": _ARRANGEMENT_ENVELOPE_NOTE
                }
                if arrangement_clip_index is not None:
                    result["arrangement_clip_index"] = arrangement_clip_index
                return result

            envelope = clip.automation_envelope(param)
            if envelope is None:
                result = {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "parameter_name": param.name,
                    "has_envelope": False,
                    "points": []
                }
                if arrangement_clip_index is not None:
                    result["arrangement_clip_index"] = arrangement_clip_index
                return result

            # Read envelope value at regular intervals across the clip
            clip_length = clip.length
            num_samples = min(int(clip_length), 64)  # Sample up to 64 points
            step = clip_length / num_samples if num_samples > 0 else 1.0
            points = []
            for i in range(num_samples):
                t = i * step
                val = envelope.value_at_time(t)
                # Normalize to 0-1
                param_range = param.max - param.min
                normalized = (val - param.min) / param_range if param_range > 0 else 0
                points.append({"time": round(t, 3), "value": round(normalized, 4)})

            result = {
                "track_index": track_index,
                "clip_index": clip_index,
                "parameter_name": param.name,
                "has_envelope": True,
                "points": points
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error getting clip envelope: " + str(e))
            raise

    def _clear_clip_envelope(self, track_index, clip_index, device_index, parameter_index, arrangement_clip_index=None):
        """Clear automation envelope for a parameter in a clip"""
        try:
            track = self._get_track(track_index)
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)

            device = track.devices[device_index]
            param = device.parameters[parameter_index]

            clip.clear_envelope(param)

            result = {
                "track_index": track_index,
                "clip_index": clip_index,
                "parameter_name": param.name,
                "cleared": True
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error clearing clip envelope: " + str(e))
            raise

    def _undo(self):
        """Undo the last action"""
        try:
            self._song.undo()
            return {"undone": True}
        except Exception as e:
            self.log_message("Error undoing: " + str(e))
            raise

    def _redo(self):
        """Redo the last undone action"""
        try:
            self._song.redo()
            return {"redone": True}
        except Exception as e:
            self.log_message("Error redoing: " + str(e))
            raise

    def _get_device_parameters(self, track_index, device_index, query=None, include_host_names=False):
        """Get parameters of a device. query filters by name/original_name/display_value."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            class_name = self._safe_getattr(device, "class_name", "") or ""
            parameters = []
            for i, p in enumerate(device.parameters):
                parameters.append(self._param_dict(i, p))
            parameters, groups = attach_groups(
                parameters,
                "{0} {1}".format(device.name, self._safe_getattr(device, "class_display_name", "") or ""),
            )
            matched = filter_parameters(parameters, query)
            if query:
                matched, groups = attach_groups(matched, device.name)
            host_names = []
            if is_plugin_class(class_name):
                host_names = self._plugin_host_parameter_names(device)
            presets = self._plugin_preset_list(device) if is_plugin_class(class_name) else []
            result = {
                "track_index": track_index,
                "track_name": track.name,
                "device_index": device_index,
                "device_name": device.name,
                "class_name": class_name,
                "class_display_name": self._safe_getattr(device, "class_display_name", "") or "",
                "type": self._get_device_type(device),
                "is_plugin": is_plugin_class(class_name),
                "configured_parameter_count": len(parameters),
                "host_parameter_count": len(host_names),
                "presets": presets,
                "selected_preset_index": self._safe_getattr(device, "selected_preset_index", None),
                "query": query,
                "grouping": "inferred_from_parameter_names",
                "groups": groups,
                "parameters": matched
            }
            note = plugin_configure_note(class_name, len(parameters), len(host_names))
            if note:
                result["note"] = note
            result["index_warning"] = (
                "Parameter indices are unique to this Configure mapping and change "
                "when knobs are added or removed. Prefer parameter_name."
            )
            coverage = mapping_coverage(
                parameters,
                "{0} {1}".format(device.name, self._safe_getattr(device, "class_display_name", "") or ""),
            )
            if coverage:
                result["coverage"] = coverage
            if include_host_names and host_names:
                result["host_parameter_names"] = host_names
            return result
        except Exception as e:
            self.log_message("Error getting device parameters: " + str(e))
            raise

    def _resolve_parameter(self, device, parameter_index, parameter_name):
        snapshots = []
        for i, p in enumerate(device.parameters):
            snapshots.append({
                "index": i,
                "name": p.name,
                "original_name": self._safe_getattr(p, "original_name", None),
            })
        found = find_parameter(snapshots, index=parameter_index, name=parameter_name)
        idx = found["index"]
        return idx, device.parameters[idx]

    def _set_device_parameter(self, track_index, device_index, parameter_index, value, parameter_name=None):
        """Set a single device parameter using a normalized value (0.0 to 1.0)"""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            _idx, parameter = self._resolve_parameter(device, parameter_index, parameter_name)
            if value < 0.0 or value > 1.0:
                raise ValueError("Normalized value must be between 0.0 and 1.0")
            actual_value = parameter.min + value * (parameter.max - parameter.min)
            parameter.value = actual_value
            return {
                "parameter_index": _idx,
                "parameter_name": parameter.name,
                "value": parameter.value,
                "normalized_value": value,
                "display_value": self._safe_getattr(parameter, "display_value", None)
            }
        except Exception as e:
            self.log_message("Error setting device parameter: " + str(e))
            raise

    def _batch_set_device_parameters(self, track_index, device_index, parameter_indices, values, parameter_names=None):
        """Set multiple device parameters at once using normalized values (0.0 to 1.0)"""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if parameter_names:
                if len(parameter_names) != len(values):
                    raise ValueError("parameter_names and values must have the same length")
                keys = parameter_names
                use_names = True
            else:
                if parameter_indices is None:
                    raise ValueError("parameter_indices or parameter_names is required")
                if len(parameter_indices) != len(values):
                    raise ValueError("parameter_indices and values must have the same length")
                keys = parameter_indices
                use_names = False
            updated = []
            skipped = []
            snapshots = []
            for i, p in enumerate(device.parameters):
                snapshots.append({
                    "index": i,
                    "name": p.name,
                    "original_name": self._safe_getattr(p, "original_name", None),
                })
            for i in range(len(keys)):
                val = values[i]
                if val < 0.0 or val > 1.0:
                    skipped.append({"name": keys[i], "reason": "value_out_of_range"})
                    continue
                if use_names:
                    found = try_find_parameter(snapshots, name=keys[i])
                    label = keys[i]
                else:
                    found = try_find_parameter(snapshots, index=keys[i])
                    label = keys[i]
                if found is None:
                    skipped.append({
                        "name": label,
                        "reason": "not_configured",
                    })
                    continue
                p_idx = found["index"]
                param = device.parameters[p_idx]
                actual_val = param.min + val * (param.max - param.min)
                param.value = actual_val
                updated.append({
                    "index": p_idx,
                    "name": param.name,
                    "value": param.value,
                    "normalized_value": val
                })
            return {
                "updated_count": len(updated),
                "skipped_count": len(skipped),
                "parameters": updated,
                "skipped": skipped,
            }
        except Exception as e:
            self.log_message("Error batch setting device parameters: " + str(e))
            raise

    def _set_plugin_preset(self, track_index, device_index, preset_index=None, preset_name=None):
        """Select a plug-in host preset by index or name (VST program bank, not Serum/Omni files)."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            class_name = self._safe_getattr(device, "class_name", "") or ""
            if not is_plugin_class(class_name):
                raise ValueError("Device is not a VST/AU plug-in")
            if not hasattr(device, "selected_preset_index"):
                raise ValueError("Plug-in does not expose selected_preset_index")
            presets = self._plugin_preset_list(device)
            if preset_name is not None and str(preset_name).strip() != "":
                needle = str(preset_name).strip().lower()
                matches = [i for i, name in enumerate(presets) if name.lower() == needle]
                if not matches:
                    matches = [i for i, name in enumerate(presets) if needle in name.lower()]
                if len(matches) != 1:
                    raise ValueError("preset_name not found or ambiguous (host bank may be empty for VST3)")
                preset_index = matches[0]
            if preset_index is None:
                raise ValueError("preset_index or preset_name is required")
            device.selected_preset_index = int(preset_index)
            return {
                "device_name": device.name,
                "selected_preset_index": device.selected_preset_index,
                "preset_name": presets[device.selected_preset_index] if 0 <= device.selected_preset_index < len(presets) else None,
                "preset_count": len(presets),
                "note": "This is the plug-in host program bank, not Serum .serumpreset files."
            }
        except Exception as e:
            self.log_message("Error setting plugin preset: " + str(e))
            raise

    def _create_midi_track(self, index):
        """Create a new MIDI track at the specified index"""
        try:
            # Create the track
            self._song.create_midi_track(index)
            
            # Get the new track
            new_track_index = len(self._song.tracks) - 1 if index == -1 else index
            new_track = self._song.tracks[new_track_index]
            
            result = {
                "index": new_track_index,
                "name": new_track.name
            }
            return result
        except Exception as e:
            self.log_message("Error creating MIDI track: " + str(e))
            raise
    
    
    def _set_track_name(self, track_index, name):
        """Set the name of a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            # Set the name
            track = self._song.tracks[track_index]
            track.name = name
            
            result = {
                "name": track.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting track name: " + str(e))
            raise
    
    def _create_clip(self, track_index, clip_index, length):
        """Create a new MIDI clip in the specified track and clip slot"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            # Check if the clip slot already has a clip
            if clip_slot.has_clip:
                raise Exception("Clip slot already has a clip")
            
            # Create the clip
            clip_slot.create_clip(length)
            
            result = {
                "name": clip_slot.clip.name,
                "length": clip_slot.clip.length
            }
            return result
        except Exception as e:
            self.log_message("Error creating clip: " + str(e))
            raise
    
    def _create_arrangement_midi_clip(self, track_index, time, length, notes=None):
        """Create a MIDI clip in the arrangement view at a given position with optional notes.

        Uses Live 11+ Track.create_midi_clip(start_time, end_time) API.
        notes: optional list of note dicts to seed the clip with.
        """
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]

            if not track.has_midi_input:
                raise Exception("Track {0} is not a MIDI track".format(track_index))

            if not hasattr(track, 'create_midi_clip'):
                raise Exception("Live version does not support Track.create_midi_clip; need Live 11+")

            start = float(time)
            length_val = float(length)
            # Live's Track.create_midi_clip takes (start_time, length) in beats,
            # not (start_time, end_time) despite some docs suggesting otherwise.
            clip = track.create_midi_clip(start, length_val)

            note_count = 0
            if notes and clip is not None:
                note_count = self._clip_add_notes(clip, notes)

            # Find this clip's index in arrangement_clips so caller can refer to it later
            arrangement_index = -1
            try:
                for i, ac in enumerate(track.arrangement_clips):
                    if abs(float(ac.start_time) - start) < 0.001:
                        arrangement_index = i
                        break
            except Exception:
                pass

            return {
                "track_index": track_index,
                "start_time": start,
                "length": float(length),
                "note_count": note_count,
                "arrangement_clip_index": arrangement_index,
                "name": clip.name if clip else "",
            }
        except Exception as e:
            self.log_message("Error creating arrangement MIDI clip: " + str(e))
            raise

    def _create_arrangement_audio_clips_batch(self, track_index, file_path, times, length=None, start_offset=None):
        """The same sample at several beat positions in one round trip (repeated hits)."""
        results = []
        for t in times:
            try:
                self._create_arrangement_audio_clip(track_index, file_path, float(t), length, start_offset)
                results.append({"time": float(t), "ok": True})
            except Exception as e:
                results.append({"time": float(t), "ok": False, "error": str(e)})
        return {"track_index": track_index, "file_path": file_path,
                "placed_count": sum(1 for r in results if r["ok"]),
                "failed_count": sum(1 for r in results if not r["ok"]), "results": results}

    def _create_arrangement_audio_clip(self, track_index, file_path, time, length=None, start_offset=None):
        """Create an audio clip from a file path in the arrangement view at a given position.

        Uses Live 11+ Track.create_audio_clip(file_path, position) API.
        length is optional: the clip loops its first `length` beats (Live 12 refuses end_time on
        a fresh arrangement audio clip, so the loop end is trimmed instead); a following clip
        truncates the region.
        start_offset (beats) skips the head of the sample (a whoosh before the hit): the
        clip's start marker is advanced by that much.
        """
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]

            if not track.has_audio_input:
                raise Exception("Track {0} is not an audio track".format(track_index))

            if not hasattr(track, 'create_audio_clip'):
                raise Exception("Live version does not support Track.create_audio_clip; need Live 11+")

            # Live 11+ API: create_audio_clip(file_path, position) returns the new Clip
            clip = track.create_audio_clip(file_path, float(time))

            length_note = ""
            if length is not None and clip is not None:
                try:
                    clip.end_time = float(time) + float(length)
                except Exception as le:
                    try:                                    # end_time may be read-only: trim the loop instead
                        clip.looping = True
                        clip.loop_end = clip.start_marker + float(length)
                    except Exception as le2:
                        length_note = "length not applied: %s / %s" % (le, le2)
                        self.log_message(length_note)
            if start_offset is not None and clip is not None:
                try:
                    clip.start_marker = clip.start_marker + float(start_offset)
                except Exception as oe:
                    self.log_message("start_offset not applied: " + str(oe))

            result = {
                "track_index": track_index,
                "file_path": file_path,
                "start_time": clip.start_time if clip else float(time),
                "length": clip.length if clip else 0,
                "start_marker": clip.start_marker if clip else None,
                "name": clip.name if clip else "",
                "note": length_note,
            }
            return result
        except Exception as e:
            self.log_message("Error creating arrangement audio clip: " + str(e))
            raise

    def _midi_note_specifications(self, notes):
        """Live 11+ MidiNoteSpecification objects. Never use set_notes (Live 11 modal)."""
        try:
            import Live
            Spec = Live.Clip.MidiNoteSpecification
        except Exception:
            raise Exception("Live.Clip.MidiNoteSpecification is not available (need Live 11+)")
        specs = []
        for note in notes:
            pitch = int(note.get("pitch", 60))
            start_time = float(note.get("start_time", 0.0))
            duration = float(note.get("duration", 0.25))
            velocity = int(note.get("velocity", 100))
            mute = bool(note.get("mute", False))
            try:
                spec = Spec(pitch=pitch, start_time=start_time, duration=duration,
                            velocity=velocity, mute=mute)
            except TypeError:
                spec = Spec(pitch, start_time, duration, velocity, mute)
            specs.append(spec)
        return tuple(specs)

    def _clip_add_notes(self, clip, notes):
        """Append notes without replacing existing notes."""
        if not notes:
            return 0
        if hasattr(clip, "add_new_notes"):
            clip.add_new_notes(self._midi_note_specifications(notes))
            return len(notes)
        if (not hasattr(clip, "replace_selected_notes") or
                not hasattr(clip, "select_all_notes") or
                not hasattr(clip, "deselect_all_notes")):
            raise Exception("No non-destructive MIDI append API is available on this Live version")
        existing = self._clip_note_dicts(clip)
        clip.deselect_all_notes()
        try:
            clip.select_all_notes()
            clip.replace_selected_notes(
                self._midi_note_specifications(existing + list(notes))
            )
        finally:
            clip.deselect_all_notes()
        return len(notes)

    def _add_notes_to_clip(self, track_index, clip_index, notes, arrangement_clip_index=None):
        """Add MIDI notes to a session clip or an arrangement MIDI clip (Live 11+ add_new_notes)."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=True,
                                      arrangement_clip_index=arrangement_clip_index)
            note_count = self._clip_add_notes(clip, notes)
            return {"note_count": note_count}
        except Exception as e:
            self.log_message("Error adding notes to clip: " + str(e))
            raise
    
    def _set_clip_name(self, track_index, clip_index, name):
        """Set the name of a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip = clip_slot.clip
            clip.name = name
            
            result = {
                "name": clip.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting clip name: " + str(e))
            raise
    
    def _set_tempo(self, tempo):
        """Set the tempo of the session"""
        try:
            self._song.tempo = tempo
            
            result = {
                "tempo": self._song.tempo
            }
            return result
        except Exception as e:
            self.log_message("Error setting tempo: " + str(e))
            raise
    
    def _fire_clip(self, track_index, clip_index):
        """Fire a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip_slot.fire()
            
            result = {
                "fired": True
            }
            return result
        except Exception as e:
            self.log_message("Error firing clip: " + str(e))
            raise
    
    def _stop_clip(self, track_index, clip_index):
        """Stop a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            clip_slot.stop()
            
            result = {
                "stopped": True
            }
            return result
        except Exception as e:
            self.log_message("Error stopping clip: " + str(e))
            raise
    
    
    def _play_arrangement(self, time=None):
        """Stop session clips, return to arrangement, optionally seek, and play."""
        try:
            self._song.stop_all_clips()
            self._song.back_to_arranger = False      # False = arrangement plays (True = session overrides it)
            if time is not None:
                self._song.current_song_time = float(time)
            self._song.start_playing()
            return {
                "playing": True,
                "position": self._song.current_song_time
            }
        except Exception as e:
            self.log_message("Error playing arrangement: " + str(e))
            raise

    def _start_playback(self):
        """Start playing the session"""
        try:
            self._song.start_playing()

            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error starting playback: " + str(e))
            raise
    
    def _stop_playback(self):
        """Stop playing the session"""
        try:
            self._song.stop_playing()
            
            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error stopping playback: " + str(e))
            raise
    
    def _get_browser_item(self, uri, path):
        """Get a browser item by URI or path"""
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            result = {
                "uri": uri,
                "path": path,
                "found": False
            }
            
            # Try to find by URI first if provided
            if uri:
                item = self._find_browser_item_by_uri(app.browser, uri)
                if item:
                    result["found"] = True
                    result["item"] = {
                        "name": item.name,
                        "is_folder": item.is_folder,
                        "is_device": item.is_device,
                        "is_loadable": item.is_loadable,
                        "uri": item.uri
                    }
                    return result
            
            # If URI not provided or not found, try by path
            if path:
                # Parse the path and navigate to the specified item
                path_parts = path.split("/")
                
                # Determine the root based on the first part
                current_item = None
                start_index = 1
                if path_parts[0].lower() == "instruments":
                    current_item = app.browser.instruments
                elif path_parts[0].lower() == "sounds":
                    current_item = app.browser.sounds
                elif path_parts[0].lower() == "drums":
                    current_item = app.browser.drums
                elif path_parts[0].lower() == "audio_effects":
                    current_item = app.browser.audio_effects
                elif path_parts[0].lower() == "midi_effects":
                    current_item = app.browser.midi_effects
                elif path_parts[0].lower() == "user_folders":
                    raw_folders = getattr(app.browser, 'user_folders', None)
                    folders = list(raw_folders) if raw_folders is not None else []
                    if len(path_parts) < 2 or not path_parts[1]:
                        result["error"] = "Path part not found"
                        return result
                    found_folder = None
                    for folder in folders:
                        if hasattr(folder, 'name') and folder.name.lower() == path_parts[1].lower():
                            found_folder = folder
                            break
                    if found_folder is None:
                        result["error"] = "Path part '{0}' not found".format(path_parts[1])
                        return result
                    current_item = found_folder
                    start_index = 2
                else:
                    # Default to instruments if not specified
                    current_item = app.browser.instruments
                    # Don't skip the first part in this case
                    path_parts = ["instruments"] + path_parts
                
                # Navigate through the path
                for i in range(start_index, len(path_parts)):
                    part = path_parts[i]
                    if not part:  # Skip empty parts
                        continue
                    
                    found = False
                    for child in current_item.children:
                        if child.name.lower() == part.lower():
                            current_item = child
                            found = True
                            break
                    
                    if not found:
                        result["error"] = "Path part '{0}' not found".format(part)
                        return result
                
                # Found the item
                result["found"] = True
                result["item"] = {
                    "name": current_item.name,
                    "is_folder": current_item.is_folder,
                    "is_device": current_item.is_device,
                    "is_loadable": current_item.is_loadable,
                    "uri": current_item.uri
                }
            
            return result
        except Exception as e:
            self.log_message("Error getting browser item: " + str(e))
            self.log_message(traceback.format_exc())
            raise   
    
    
    
    def _load_browser_item(self, track_index, item_uri, clip_index=None):
        """Load a browser item onto a track by its URI. Use -1 for master track.
        If clip_index is provided, selects that clip slot before loading (needed for .alc clips)."""
        try:
            track = self._get_track(track_index)

            # Access the application's browser instance instead of creating a new one
            app = self.application()

            # Find the browser item by URI
            item = self._find_browser_item_by_uri(app.browser, item_uri)

            if not item:
                raise ValueError("Browser item with URI '{0}' not found".format(item_uri))

            # Select the track
            self._song.view.selected_track = track

            # If clip_index provided, select that clip slot so .alc clips land there
            if clip_index is not None and hasattr(track, 'clip_slots'):
                if clip_index < len(track.clip_slots):
                    self._song.view.highlighted_clip_slot = track.clip_slots[clip_index]

            # Load the item
            app.browser.load_item(item)
            
            result = {
                "loaded": True,
                "item_name": item.name,
                "track_name": track.name,
                "uri": item_uri
            }
            return result
        except Exception as e:
            self.log_message("Error loading browser item: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    def _find_browser_item_by_uri(self, browser_or_item, uri, max_depth=10, current_depth=0):
        """Find a browser item by its URI"""
        try:
            # Check if this is the item we're looking for
            if hasattr(browser_or_item, 'uri') and browser_or_item.uri == uri:
                return browser_or_item
            
            # Stop recursion if we've reached max depth
            if current_depth >= max_depth:
                return None
            
            # Check if this is a browser with root categories
            if hasattr(browser_or_item, 'instruments'):
                # Check all main categories
                categories = [
                    browser_or_item.instruments,
                    browser_or_item.sounds,
                    browser_or_item.drums,
                    browser_or_item.audio_effects,
                    browser_or_item.midi_effects,
                ]
                # Add optional categories that may not exist on all versions
                for attr in ['clips', 'samples', 'packs', 'user_library', 'current_project', 'max_for_live']:
                    if hasattr(browser_or_item, attr):
                        cat = getattr(browser_or_item, attr)
                        if cat is not None:
                            categories.append(cat)
                # user_folders is a list of Places roots, not a single item with .children
                if hasattr(browser_or_item, 'user_folders'):
                    try:
                        folders = browser_or_item.user_folders
                        if folders is not None:
                            for folder in folders:
                                if folder is not None:
                                    categories.append(folder)
                    except Exception:
                        pass
                
                for category in categories:
                    item = self._find_browser_item_by_uri(category, uri, max_depth, current_depth + 1)
                    if item:
                        return item
                
                return None
            
            # Check if this item has children
            if hasattr(browser_or_item, 'children') and browser_or_item.children:
                for child in browser_or_item.children:
                    item = self._find_browser_item_by_uri(child, uri, max_depth, current_depth + 1)
                    if item:
                        return item
            
            return None
        except Exception as e:
            self.log_message("Error finding browser item by URI: {0}".format(str(e)))
            return None
    
    # Helper methods
    
    # ------------------------------------------------------------------
    # Clip editing, device bypass, return tracks, drum pads
    # (ported from the missing-features branch: the subset an agent
    # actually reaches for; see MISSING_FEATURES.md for the rest)
    # ------------------------------------------------------------------
    def _session_clip(self, track_index, clip_index, midi=None, arrangement_clip_index=None):
        """A clip: session slot `clip_index`, or `track.arrangement_clips[arrangement_clip_index]`
        when that is given (audio clips can only be created in the arrangement over the socket).
        `midi` True/False asserts the clip type."""
        track = self._get_track(track_index)
        if arrangement_clip_index is not None:
            clips = self._get_arrangement_clips_safe(track)
            if arrangement_clip_index < 0 or arrangement_clip_index >= len(clips):
                raise IndexError("Arrangement clip index out of range")
            clip = clips[arrangement_clip_index]
        else:
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            slot = track.clip_slots[clip_index]
            if not slot.has_clip:
                raise Exception("No clip in slot {0} of track {1}".format(clip_index, track_index))
            clip = slot.clip
        if midi is True and not clip.is_midi_clip:
            raise Exception("Not a MIDI clip")
        if midi is False and not clip.is_audio_clip:
            raise Exception("Not an audio clip")
        return clip

    def _clip_is_arrangement(self, clip, arrangement_clip_index=None):
        if arrangement_clip_index is not None:
            return True
        flag = self._safe_getattr(clip, "is_arrangement_clip", None)
        if flag is not None:
            return bool(flag)
        return False

    def _apply_color(self, obj, color_index=None, color=None):
        if color_index is None and color is None:
            raise Exception("Provide color_index and/or color")
        if color_index is not None:
            obj.color_index = int(color_index)
        if color is not None:
            obj.color = int(color)
        return {
            "color_index": self._safe_getattr(obj, "color_index", None),
            "color": self._safe_getattr(obj, "color", None)
        }

    def _normalized_panning(self, panning):
        """Track-style pan: 0.0 left, 1.0 right. Negative values are treated as -1..1."""
        panning = float(panning)
        if panning < 0.0:
            if panning < -1.0:
                raise ValueError("Panning must be 0.0-1.0 (or -1.0-1.0 when negative)")
            panning = (panning + 1.0) / 2.0
        elif panning > 1.0:
            raise ValueError("Panning must be 0.0-1.0 (or -1.0-1.0 when negative)")
        return panning

    def _remove_notes(self, track_index, clip_index, from_pitch, pitch_span, from_time, time_span, aci=None):
        """Remove the notes inside a pitch/time window. time_span < 0 = to the end of the clip."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=True, arrangement_clip_index=aci)
            if time_span is None or time_span < 0:
                time_span = max(clip.length - from_time, 0.0)
            before = len(clip.get_notes_extended(0, 128, 0.0, clip.length))
            clip.remove_notes_extended(from_pitch, pitch_span, from_time, time_span)
            after = len(clip.get_notes_extended(0, 128, 0.0, clip.length))
            return {"removed": before - after, "remaining": after}
        except Exception as e:
            self.log_message("Error removing notes: " + str(e))
            raise

    def _quantize_clip(self, track_index, clip_index, grid, strength, aci=None):
        """clip.quantize(grid, strength); grid is Live's RecordingQuantization enum, verified
        on Live 12: 1=1/4, 2=1/8, 3=1/8+1/8T, 4=1/8T, 5=1/16, 6=1/16+1/16T, 7=1/16T, 8=1/32."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=aci)
            clip.quantize(int(grid), float(strength))
            return {"quantized": True, "grid": int(grid), "strength": float(strength)}
        except Exception as e:
            self.log_message("Error quantizing clip: " + str(e))
            raise

    def _duplicate_clip_loop(self, track_index, clip_index, aci=None):
        """Double the loop and copy its contents into the new half."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=aci)
            clip.duplicate_loop()
            return {"length": clip.length, "loop_start": clip.loop_start, "loop_end": clip.loop_end}
        except Exception as e:
            self.log_message("Error duplicating clip loop: " + str(e))
            raise

    def _duplicate_region(self, track_index, clip_index, region_start, region_length, destination_time,
                          pitch=-1, transposition_amount=0, aci=None):
        """Copy [region_start, +region_length) to destination_time; pitch -1 = all pitches."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=True, arrangement_clip_index=aci)
            clip.duplicate_region(float(region_start), float(region_length), float(destination_time),
                                  int(pitch), int(transposition_amount))
            return {"duplicated": True, "length": clip.length}
        except Exception as e:
            self.log_message("Error duplicating region: " + str(e))
            raise

    def _set_device_enabled(self, track_index, device_index, enabled):
        """Bypass / re-enable a device through its 'Device On' parameter (works for master and returns too)."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            for param in device.parameters:
                if param.name == "Device On":
                    param.value = 1.0 if enabled else 0.0
                    return {"enabled": bool(enabled), "device_name": device.name}
            raise Exception("Device has no 'Device On' parameter")
        except Exception as e:
            self.log_message("Error setting device enabled: " + str(e))
            raise

    def _create_return_track(self):
        try:
            self._song.create_return_track()
            return {"return_track_count": len(self._song.return_tracks), "name": self._song.return_tracks[-1].name}
        except Exception as e:
            self.log_message("Error creating return track: " + str(e))
            raise

    def _delete_return_track(self, index):
        try:
            if index < 0 or index >= len(self._song.return_tracks):
                raise IndexError("Return track index out of range")
            self._song.delete_return_track(index)
            return {"return_track_count": len(self._song.return_tracks)}
        except Exception as e:
            self.log_message("Error deleting return track: " + str(e))
            raise

    def _stop_all_clips(self, quantized=True):
        try:
            self._song.stop_all_clips(bool(quantized))
            return {"stopped": True}
        except Exception as e:
            self.log_message("Error stopping all clips: " + str(e))
            raise

    def _get_drum_pads(self, track_index, device_index):
        """The filled pads of a Drum Rack: note number, pad name, and the device on the pad."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not hasattr(device, "drum_pads"):
                raise Exception("Device '{0}' is not a Drum Rack".format(device.name))
            pads = []
            for pad in device.drum_pads:
                if not pad.chains:
                    continue
                info = {"note": pad.note, "name": pad.name, "mute": pad.mute, "solo": pad.solo}
                if pad.chains[0].devices:
                    info["device"] = pad.chains[0].devices[0].name
                pads.append(info)
            return {"device": device.name, "pads": pads, "total_pads": len(device.drum_pads)}
        except Exception as e:
            self.log_message("Error getting drum pads: " + str(e))
            raise

    def _set_clip_gain(self, track_index, clip_index, gain, aci=None):
        """Audio clip gain, normalized 0-1 (0.4 is about 0 dB)."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=False, arrangement_clip_index=aci)
            clip.gain = float(gain)
            return {"gain": clip.gain, "gain_display": getattr(clip, "gain_display_string", "")}
        except Exception as e:
            self.log_message("Error setting clip gain: " + str(e))
            raise

    def _set_clip_pitch(self, track_index, clip_index, coarse=None, fine=None, aci=None):
        """Audio clip transpose: coarse in semitones (-48..48), fine in cents (-500..500)."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=False, arrangement_clip_index=aci)
            if coarse is not None:
                clip.pitch_coarse = int(coarse)
            if fine is not None:
                clip.pitch_fine = int(fine)
            return {"pitch_coarse": clip.pitch_coarse, "pitch_fine": clip.pitch_fine}
        except Exception as e:
            self.log_message("Error setting clip pitch: " + str(e))
            raise

    def _set_clip_warping(self, track_index, clip_index, warping, aci=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=False, arrangement_clip_index=aci)
            clip.warping = bool(warping)
            return {"warping": clip.warping}
        except Exception as e:
            self.log_message("Error setting clip warping: " + str(e))
            raise

    def _set_clip_warp_mode(self, track_index, clip_index, warp_mode, aci=None):
        """0=Beats, 1=Tones, 2=Texture, 3=Re-Pitch, 4=Complex, 6=Complex Pro (warping must be on)."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=False, arrangement_clip_index=aci)
            clip.warp_mode = int(warp_mode)
            return {"warp_mode": clip.warp_mode}
        except Exception as e:
            self.log_message("Error setting clip warp mode: " + str(e))
            raise

    def _get_clip_info(self, track_index, clip_index, arrangement_clip_index=None):
        """Everything about one clip: length, loop and markers, mute, and for audio clips
        warping, warp mode, pitch, gain, file. Session slot or arrangement clip."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            info = {
                "name": clip.name, "length": clip.length, "is_midi_clip": clip.is_midi_clip,
                "is_audio_clip": clip.is_audio_clip, "looping": clip.looping,
                "loop_start": clip.loop_start, "loop_end": clip.loop_end,
                "start_marker": clip.start_marker, "end_marker": clip.end_marker,
                "muted": clip.muted, "is_playing": clip.is_playing, "is_recording": clip.is_recording,
                "color_index": clip.color_index,
            }
            if arrangement_clip_index is not None:
                info["start_time"] = clip.start_time; info["end_time"] = clip.end_time
            else:
                info["launch_mode"] = clip.launch_mode; info["launch_quantization"] = clip.launch_quantization
            if clip.is_audio_clip:
                info.update({"warping": clip.warping, "warp_mode": clip.warp_mode, "pitch_coarse": clip.pitch_coarse,
                             "pitch_fine": clip.pitch_fine, "gain": clip.gain,
                             "gain_display": getattr(clip, "gain_display_string", ""), "file_path": clip.file_path,
                             "sample_length": getattr(clip, "sample_length", None)})
                ram_mode = self._safe_getattr(clip, "ram_mode", None)
                if ram_mode is not None:
                    info["ram_mode"] = ram_mode
            sig_num = self._safe_getattr(clip, "signature_numerator", None)
            if sig_num is not None:
                info["signature_numerator"] = sig_num
            sig_den = self._safe_getattr(clip, "signature_denominator", None)
            if sig_den is not None:
                info["signature_denominator"] = sig_den
            has_groove = self._safe_getattr(clip, "has_groove", None)
            if has_groove is not None:
                info["has_groove"] = bool(has_groove)
            return info
        except Exception as e:
            self.log_message("Error getting clip info: " + str(e))
            raise

    def _resample_master(self, seconds=None, name="master rec", start_time=0.0):
        """Record the main output to an audio file: an audio track on Resampling, armed alone,
        arrangement playing from start_time with record mode on, until the last arrangement
        clip ends (or `seconds`). Returns the recorded clip's file path. Runs on the socket
        thread like record_arrangement; Live's own state is touched on the main thread."""
        import time as time_module
        holder = {"track": None, "index": None}
        def do_on_main(fn):
            done = threading.Event(); err = [None]
            def task():
                try:
                    fn()
                except Exception as e:
                    err[0] = e
                done.set()
            self.schedule_message(0, task)
            done.wait(timeout=5.0)
            if err[0]:
                raise err[0]
        try:
            tempo = self._song.tempo
            end_beat = 0.0
            for tr in self._song.tracks:
                for c in self._get_arrangement_clips_safe(tr):
                    end_beat = max(end_beat, c.end_time)
            if seconds is None:
                if end_beat <= start_time:
                    raise Exception("nothing in the arrangement to record (pass `seconds` to record anyway)")
                seconds = (end_beat - start_time + 4.0) * 60.0 / tempo
            def make_track():
                if self._song.is_playing:
                    self._song.stop_playing()
                self._song.create_audio_track(-1)
                track = self._song.tracks[-1]
                track.name = name
                for rt in track.available_input_routing_types:
                    if str(rt.display_name) == "Resampling":
                        track.input_routing_type = rt
                        break
                else:
                    raise Exception("no Resampling input on the new track")
                holder["track"] = track; holder["index"] = list(self._song.tracks).index(track)
            def route_and_arm():
                track = holder["track"]
                chans = list(track.available_input_routing_channels)
                if chans:
                    track.input_routing_channel = chans[0]
                track.current_monitoring_state = 2          # Off: never feed the main mix back into itself
                for tr in self._song.tracks:                # Live auto-arms new tracks; an armed MIDI track in
                    if tr.can_be_armed and tr.arm:          # record mode records over its clip instead of playing
                        tr.arm = False
                track.arm = True
            def locate():
                self._song.back_to_arranger = False        # the arrangement plays (True = session overrides it)
                self._song.current_song_time = float(start_time)
            def record_on():
                self._song.record_mode = 1
            def go():
                self._song.stop_all_clips()
                self._song.back_to_arranger = False
                self._song.current_song_time = float(start_time)
                self._song.start_playing()
            # the same steps as separate socket calls work; one combined task did not start the transport
            for step in (make_track, route_and_arm, locate, record_on, go):
                do_on_main(step)
                time_module.sleep(0.15)
            state = {"playing": True, "pos": 0.0}
            def read_state():
                state["playing"] = bool(self._song.is_playing); state["pos"] = float(self._song.current_song_time)
            t0 = time_module.monotonic(); stopped_early = False
            time_module.sleep(1.0)                          # let the transport start before watching it
            while time_module.monotonic() - t0 < seconds:
                time_module.sleep(0.5)
                do_on_main(read_state)                      # LOM reads are only reliable on the main thread
                if not state["playing"]:
                    stopped_early = True
                    break
            out = {}
            def finish():
                self._song.stop_playing()
                self._song.record_mode = 0
                holder["track"].arm = False
                self._song.current_song_time = float(start_time)
            def read_clip():
                clips = self._get_arrangement_clips_safe(holder["track"])
                rec = clips[-1] if clips else None
                out["file_path"] = rec.file_path if rec else None
                out["length_beats"] = rec.length if rec else 0.0
            do_on_main(finish)
            for _ in range(12):                              # the recorded clip appears a moment after stop
                time_module.sleep(0.5)
                do_on_main(read_clip)
                if out.get("file_path"):
                    break
            return {"track_index": holder["index"], "track_name": name,
                    "file_path": out.get("file_path"), "length_beats": out.get("length_beats", 0.0),
                    "seconds": round(seconds, 1), "stopped_at_beat": state["pos"], "stopped_early": stopped_early,
                    "note": "the transport stopped before the end (audio device change or a manual stop?)" if stopped_early else ""}
        except Exception as e:
            self.log_message("Error resampling master: " + str(e))
            raise

    def _get_device_type(self, device):
        """Get the type of a device"""
        try:
            return classify_device(
                self._safe_getattr(device, "class_name", "") or "",
                self._safe_getattr(device, "class_display_name", "") or "",
                self._safe_getattr(device, "type", 0),
                bool(self._safe_getattr(device, "can_have_drum_pads", False)),
                bool(self._safe_getattr(device, "can_have_chains", False)),
            )
        except Exception:
            return "unknown"

    def _param_dict(self, index, param):
        span = param.max - param.min
        norm_val = 0
        if span != 0:
            norm_val = (param.value - param.min) / span
        display = None
        try:
            if hasattr(param, "str_for_value"):
                display = param.str_for_value(param.value)
        except Exception:
            display = None
        if display is None:
            display = self._safe_getattr(param, "display_value", None)
        items = None
        if self._safe_getattr(param, "is_quantized", False):
            raw_items = self._safe_getattr(param, "value_items", None)
            if raw_items is not None:
                try:
                    items = [str(x) for x in list(raw_items)]
                except Exception:
                    items = None
        info = {
            "index": index,
            "id": normalize_param_key(param.name),
            "name": param.name,
            "original_name": self._safe_getattr(param, "original_name", None),
            "value": param.value,
            "normalized_value": norm_val,
            "min": param.min,
            "max": param.max,
            "is_quantized": param.is_quantized,
            "is_enabled": param.is_enabled,
            "display_value": display,
            "automation_state": self._safe_getattr(param, "automation_state", None),
        }
        if items is not None:
            info["value_items"] = items
        return info

    def _plugin_host_parameter_names(self, device):
        if not hasattr(device, "get_parameter_names"):
            return []
        try:
            names = device.get_parameter_names(0, -1)
            return [str(n) for n in list(names)]
        except Exception:
            return []

    def _plugin_preset_list(self, device):
        raw = self._safe_getattr(device, "presets", None)
        if raw is None:
            return []
        try:
            return [str(x) for x in list(raw)]
        except Exception:
            return []
    
    def get_browser_tree(self, category_type="all"):
        """
        Get a simplified tree of browser categories.
        
        Args:
            category_type: Type of categories to get ('all', 'instruments', 'sounds', etc.)
            
        Returns:
            Dictionary with the browser tree structure
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            # Log available browser attributes to help diagnose issues
            browser_attrs = [attr for attr in dir(app.browser) if not attr.startswith('_')]
            self.log_message("Available browser attributes: {0}".format(browser_attrs))
            
            result = {
                "type": category_type,
                "categories": [],
                "available_categories": browser_attrs
            }
            
            # Helper function to process a browser item and its children
            def process_item(item, depth=0):
                if not item:
                    return None
                
                result = {
                    "name": item.name if hasattr(item, 'name') else "Unknown",
                    "is_folder": hasattr(item, 'children') and bool(item.children),
                    "is_device": hasattr(item, 'is_device') and item.is_device,
                    "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
                    "uri": item.uri if hasattr(item, 'uri') else None,
                    "children": []
                }
                
                
                return result
            
            # Process based on category type and available attributes
            if (category_type == "all" or category_type == "instruments") and hasattr(app.browser, 'instruments'):
                try:
                    instruments = process_item(app.browser.instruments)
                    if instruments:
                        instruments["name"] = "Instruments"  # Ensure consistent naming
                        result["categories"].append(instruments)
                except Exception as e:
                    self.log_message("Error processing instruments: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "sounds") and hasattr(app.browser, 'sounds'):
                try:
                    sounds = process_item(app.browser.sounds)
                    if sounds:
                        sounds["name"] = "Sounds"  # Ensure consistent naming
                        result["categories"].append(sounds)
                except Exception as e:
                    self.log_message("Error processing sounds: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "drums") and hasattr(app.browser, 'drums'):
                try:
                    drums = process_item(app.browser.drums)
                    if drums:
                        drums["name"] = "Drums"  # Ensure consistent naming
                        result["categories"].append(drums)
                except Exception as e:
                    self.log_message("Error processing drums: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "audio_effects") and hasattr(app.browser, 'audio_effects'):
                try:
                    audio_effects = process_item(app.browser.audio_effects)
                    if audio_effects:
                        audio_effects["name"] = "Audio Effects"  # Ensure consistent naming
                        result["categories"].append(audio_effects)
                except Exception as e:
                    self.log_message("Error processing audio_effects: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "midi_effects") and hasattr(app.browser, 'midi_effects'):
                try:
                    midi_effects = process_item(app.browser.midi_effects)
                    if midi_effects:
                        midi_effects["name"] = "MIDI Effects"
                        result["categories"].append(midi_effects)
                except Exception as e:
                    self.log_message("Error processing midi_effects: {0}".format(str(e)))

            # user_folders is a list of Places roots, not a single item with .children
            if (category_type == "all" or category_type == "user_folders") and hasattr(app.browser, 'user_folders'):
                try:
                    folder_children = []
                    raw_folders = app.browser.user_folders
                    folders = list(raw_folders) if raw_folders is not None else []
                    for folder in folders:
                        folder_children.append({
                            "name": folder.name if hasattr(folder, 'name') else "Unknown",
                            "is_folder": hasattr(folder, 'children') and bool(folder.children),
                            "is_device": hasattr(folder, 'is_device') and folder.is_device,
                            "is_loadable": hasattr(folder, 'is_loadable') and folder.is_loadable,
                            "uri": folder.uri if hasattr(folder, 'uri') else None,
                            "children": []
                        })
                    result["categories"].append({
                        "name": "User Folders",
                        "is_folder": True,
                        "is_device": False,
                        "is_loadable": False,
                        "uri": None,
                        "children": folder_children
                    })
                except Exception as e:
                    self.log_message("Error processing user_folders: {0}".format(str(e)))
            
            # Try to process other potentially available categories
            for attr in browser_attrs:
                if attr not in ['instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects', 'user_folders'] and \
                   (category_type == "all" or category_type == attr):
                    try:
                        item = getattr(app.browser, attr)
                        if hasattr(item, 'children') or hasattr(item, 'name'):
                            category = process_item(item)
                            if category:
                                category["name"] = attr.capitalize()
                                result["categories"].append(category)
                    except Exception as e:
                        self.log_message("Error processing {0}: {1}".format(attr, str(e)))
            
            self.log_message("Browser tree generated for {0} with {1} root categories".format(
                category_type, len(result['categories'])))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser tree: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    def get_browser_items_at_path(self, path):
        """
        Get browser items at a specific path.
        
        Args:
            path: Path in the format "category/folder/subfolder"
                 where category is one of: instruments, sounds, drums, audio_effects, midi_effects
                 or any other available browser category
                 
        Returns:
            Dictionary with items at the specified path
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            # Log available browser attributes to help diagnose issues
            browser_attrs = [attr for attr in dir(app.browser) if not attr.startswith('_')]
            self.log_message("Available browser attributes: {0}".format(browser_attrs))
                
            # Parse the path
            path_parts = path.split("/")
            if not path_parts:
                raise ValueError("Invalid path")
            
            # Determine the root category
            root_category = path_parts[0].lower()
            current_item = None
            
            # Check standard categories first
            if root_category == "instruments" and hasattr(app.browser, 'instruments'):
                current_item = app.browser.instruments
            elif root_category == "sounds" and hasattr(app.browser, 'sounds'):
                current_item = app.browser.sounds
            elif root_category == "drums" and hasattr(app.browser, 'drums'):
                current_item = app.browser.drums
            elif root_category == "audio_effects" and hasattr(app.browser, 'audio_effects'):
                current_item = app.browser.audio_effects
            elif root_category == "midi_effects" and hasattr(app.browser, 'midi_effects'):
                current_item = app.browser.midi_effects
            elif root_category == "user_folders" and hasattr(app.browser, 'user_folders'):
                raw_folders = app.browser.user_folders
                folders = list(raw_folders) if raw_folders is not None else []
                remaining = [p for p in path_parts[1:] if p]
                if not remaining:
                    items = []
                    for folder in folders:
                        items.append({
                            "name": folder.name if hasattr(folder, 'name') else "Unknown",
                            "is_folder": hasattr(folder, 'children') and bool(folder.children),
                            "is_device": hasattr(folder, 'is_device') and folder.is_device,
                            "is_loadable": hasattr(folder, 'is_loadable') and folder.is_loadable,
                            "uri": folder.uri if hasattr(folder, 'uri') else None
                        })
                    result = {
                        "path": path,
                        "name": "User Folders",
                        "uri": None,
                        "is_folder": True,
                        "is_device": False,
                        "is_loadable": False,
                        "items": items
                    }
                    self.log_message("Retrieved {0} items at path: {1}".format(len(items), path))
                    return result
                found = False
                for folder in folders:
                    if hasattr(folder, 'name') and folder.name.lower() == remaining[0].lower():
                        current_item = folder
                        found = True
                        break
                if not found:
                    return {
                        "path": path,
                        "error": "Path part '{0}' not found".format(remaining[0]),
                        "items": []
                    }
                path_parts = [root_category] + remaining[1:]
            else:
                # Try to find the category in other browser attributes
                found = False
                for attr in browser_attrs:
                    if attr.lower() == root_category:
                        try:
                            current_item = getattr(app.browser, attr)
                            found = True
                            break
                        except Exception as e:
                            self.log_message("Error accessing browser attribute {0}: {1}".format(attr, str(e)))
                
                if not found:
                    # If we still haven't found the category, return available categories
                    return {
                        "path": path,
                        "error": "Unknown or unavailable category: {0}".format(root_category),
                        "available_categories": browser_attrs,
                        "items": []
                    }
            
            # Navigate through the path
            for i in range(1, len(path_parts)):
                part = path_parts[i]
                if not part:  # Skip empty parts
                    continue
                
                if not hasattr(current_item, 'children'):
                    return {
                        "path": path,
                        "error": "Item at '{0}' has no children".format('/'.join(path_parts[:i])),
                        "items": []
                    }
                
                found = False
                for child in current_item.children:
                    if hasattr(child, 'name') and child.name.lower() == part.lower():
                        current_item = child
                        found = True
                        break
                
                if not found:
                    return {
                        "path": path,
                        "error": "Path part '{0}' not found".format(part),
                        "items": []
                    }
            
            # Get items at the current path
            items = []
            if hasattr(current_item, 'children'):
                for child in current_item.children:
                    item_info = {
                        "name": child.name if hasattr(child, 'name') else "Unknown",
                        "is_folder": hasattr(child, 'children') and bool(child.children),
                        "is_device": hasattr(child, 'is_device') and child.is_device,
                        "is_loadable": hasattr(child, 'is_loadable') and child.is_loadable,
                        "uri": child.uri if hasattr(child, 'uri') else None
                    }
                    items.append(item_info)
            
            result = {
                "path": path,
                "name": current_item.name if hasattr(current_item, 'name') else "Unknown",
                "uri": current_item.uri if hasattr(current_item, 'uri') else None,
                "is_folder": hasattr(current_item, 'children') and bool(current_item.children),
                "is_device": hasattr(current_item, 'is_device') and current_item.is_device,
                "is_loadable": hasattr(current_item, 'is_loadable') and current_item.is_loadable,
                "items": items
            }
            
            self.log_message("Retrieved {0} items at path: {1}".format(len(items), path))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser items at path: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise

    def _device_chain_role(self, device):
        dtype = self._get_device_type(device)
        class_name = (self._safe_getattr(device, "class_name", "") or "").lower()
        live_type = str(self._safe_getattr(device, "type", "") or "").lower()
        blob = " ".join([str(dtype), class_name, live_type])
        if "midi_effect" in blob:
            return "midi_effect"
        if dtype in ("instrument", "drum_machine"):
            return "instrument"
        if "instrument" in class_name or "instrument" in live_type:
            return "instrument"
        if "drumgroup" in class_name:
            return "instrument"
        return dtype

    def _instrument_would_precede_midi_fx(self, track, device_index, target_index):
        devices = list(track.devices)
        if device_index < 0 or device_index >= len(devices):
            return False
        if self._device_chain_role(devices[device_index]) != "instrument":
            return False
        inst_new = int(target_index)
        for i, other in enumerate(devices):
            if i == device_index:
                continue
            if self._device_chain_role(other) != "midi_effect":
                continue
            other_new = i
            if device_index < i and inst_new > i:
                other_new = i - 1
            elif device_index > i and inst_new <= i:
                other_new = i + 1
            if inst_new < other_new:
                return True
        return False

    def _move_device(self, track_index, device_index, target_index):
        """Reorder devices on a track. Live will not place an instrument before MIDI effects."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            device_name = device.name
            target_index = int(target_index)
            if target_index != device_index and self._instrument_would_precede_midi_fx(track, device_index, target_index):
                raise Exception(_MOVE_DEVICE_INSTRUMENT_MSG)
            try:
                self._song.move_device(device, track, target_index)
            except Exception as e:
                msg = str(e)
                if "Couldn't move device" in msg or "Could not move device" in msg:
                    raise Exception("{0} Original: {1}".format(_MOVE_DEVICE_INSTRUMENT_MSG, msg))
                raise
            return {"moved": True, "device_name": device_name, "target_index": target_index}
        except Exception as e:
            self.log_message("Error moving device: " + str(e))
            raise

    def _get_groove_pool(self):
        """List grooves in the song groove pool plus the global groove amount."""
        try:
            grooves = []
            pool = self._safe_getattr(self._song, "groove_pool", None)
            raw = self._safe_getattr(pool, "grooves", None) if pool is not None else None
            if raw is not None:
                for i, groove in enumerate(raw):
                    grooves.append({
                        "index": i,
                        "name": self._safe_getattr(groove, "name", ""),
                        "timing_amount": self._safe_getattr(groove, "timing_amount", None),
                        "quantization_amount": self._safe_getattr(groove, "quantization_amount", None),
                        "velocity_amount": self._safe_getattr(groove, "velocity_amount", None),
                        "random_amount": self._safe_getattr(groove, "random_amount", None)
                    })
            return {
                "groove_amount": self._safe_getattr(self._song, "groove_amount", None),
                "grooves": grooves
            }
        except Exception as e:
            self.log_message("Error getting groove pool: " + str(e))
            raise

    def _set_groove_amount(self, amount):
        """Set the song-wide groove amount (0.0-1.0)."""
        try:
            amount = float(amount)
            if amount < 0.0 or amount > 1.0:
                raise ValueError("amount must be between 0.0 and 1.0")
            self._song.groove_amount = amount
            return {"groove_amount": self._song.groove_amount}
        except Exception as e:
            self.log_message("Error setting groove amount: " + str(e))
            raise

    def _apply_groove(self, track_index, clip_index, groove_index, arrangement_clip_index=None):
        """Assign a groove-pool groove to a clip."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            pool = self._safe_getattr(self._song, "groove_pool", None)
            grooves = self._safe_getattr(pool, "grooves", None) if pool is not None else None
            if grooves is None:
                raise Exception("Groove pool not available")
            if groove_index < 0 or groove_index >= len(grooves):
                raise IndexError("Groove index out of range")
            groove = grooves[groove_index]
            clip.groove = groove
            result = {
                "applied": True,
                "groove_index": groove_index,
                "groove_name": self._safe_getattr(groove, "name", "")
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error applying groove: " + str(e))
            raise

    def _iter_song_clips(self):
        tracks = []
        try:
            tracks.extend(list(self._song.tracks))
        except Exception:
            pass
        try:
            tracks.append(self._song.master_track)
        except Exception:
            pass
        try:
            tracks.extend(list(self._song.return_tracks))
        except Exception:
            pass
        for track in tracks:
            slots = self._safe_getattr(track, "clip_slots", None)
            if slots is not None:
                try:
                    slot_list = list(slots)
                except Exception:
                    slot_list = []
                for slot in slot_list:
                    if self._safe_getattr(slot, "has_clip", False):
                        other = self._safe_getattr(slot, "clip", None)
                        if other is not None:
                            yield other
            for other in self._get_arrangement_clips_safe(track):
                if other is not None:
                    yield other

    def _is_null_groove(self, groove):
        if groove is None:
            return True
        try:
            if not groove:
                return True
        except Exception:
            pass
        return False

    def _groove_is_cleared(self, clip):
        has = self._safe_getattr(clip, "has_groove", None)
        if has is not None:
            return not bool(has)
        return self._is_null_groove(self._safe_getattr(clip, "groove", None))

    def _find_ungrooved_handle(self, exclude_clip):
        for other in self._iter_song_clips():
            if other is exclude_clip:
                continue
            if self._groove_is_cleared(other):
                handle = self._safe_getattr(other, "groove", None)
                if handle is not None:
                    return handle
        return None

    def _assign_groove_from_temp_clip(self, clip):
        temp_index = None
        try:
            self._song.create_midi_track(-1)
            temp_index = len(self._song.tracks) - 1
            temp_track = self._song.tracks[temp_index]
            slots = temp_track.clip_slots
            if slots is None or len(slots) == 0:
                return None
            slot = slots[0]
            if not slot.has_clip:
                slot.create_clip(4.0)
            handle = self._safe_getattr(slot.clip, "groove", None)
            if handle is not None:
                clip.groove = handle
            return handle
        finally:
            if temp_index is not None:
                try:
                    self._song.delete_track(temp_index)
                except Exception:
                    pass

    def _construct_empty_groove(self):
        try:
            import Live
        except Exception:
            return None
        owners = []
        for name in ("Groove", "Clip", "Song"):
            owner = getattr(Live, name, None)
            if owner is not None:
                owners.append(owner)
        owners.append(Live)
        for owner in owners:
            try:
                attrs = dir(owner)
            except Exception:
                continue
            for attr in attrs:
                if "Groove" not in attr:
                    continue
                cls = getattr(owner, attr, None)
                if cls is None:
                    continue
                try:
                    obj = cls()
                    if obj is not None:
                        return obj
                except Exception:
                    continue
        return None

    def _try_assign_groove(self, clip, value):
        clip.groove = value
        return self._groove_is_cleared(clip)

    def _clear_clip_groove(self, track_index, clip_index, arrangement_clip_index=None):
        """Unassign clip.groove. Live rejects Python None; try 0/False and an ungrooved clip handle."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            if self._groove_is_cleared(clip):
                result = {"cleared": True, "already_clear": True}
                if arrangement_clip_index is not None:
                    result["arrangement_clip_index"] = arrangement_clip_index
                return result
            last_err = None
            for candidate in (0, False):
                try:
                    if self._try_assign_groove(clip, candidate):
                        last_err = None
                        break
                except Exception as e:
                    last_err = e
            if not self._groove_is_cleared(clip):
                try:
                    handle = self._find_ungrooved_handle(clip)
                    if handle is not None:
                        self._try_assign_groove(clip, handle)
                except Exception as e:
                    last_err = e
            if not self._groove_is_cleared(clip):
                try:
                    self._assign_groove_from_temp_clip(clip)
                except Exception as e:
                    last_err = e
            if not self._groove_is_cleared(clip):
                try:
                    constructed = self._construct_empty_groove()
                    if constructed is not None:
                        self._try_assign_groove(clip, constructed)
                except Exception as e:
                    last_err = e
            if not self._groove_is_cleared(clip):
                extra = "; {0}".format(str(last_err)) if last_err else ""
                raise Exception(
                    "Could not clear clip groove: Live still reports the clip as grooved. "
                    "Python cannot assign a null TPyHandle<AAbstractGroove> (None is rejected){0}".format(extra)
                )
            result = {"cleared": True}
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error clearing clip groove: " + str(e))
            raise

    def _get_device_sidechain(self, track_index, device_index):
        """Read a device's sidechain/input routing if the device exposes it."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            class_name = self._safe_getattr(device, "class_name", "")
            name = self._safe_getattr(device, "name", "")
            if not hasattr(device, "input_routing_type"):
                return {
                    "supported": False,
                    "class_name": class_name,
                    "name": name,
                    "note": "Device has no input_routing_type (not a sidechain-capable device)"
                }
            result = {
                "supported": True,
                "class_name": class_name,
                "name": name,
                "input_routing_type": str(device.input_routing_type.display_name) if hasattr(device.input_routing_type, 'display_name') else str(device.input_routing_type),
            }
            try:
                ch = getattr(device, "input_routing_channel", None)
                result["input_routing_channel"] = str(ch.display_name) if ch is not None else None
                result["available_input_routing_channels"] = [str(c.display_name) for c in device.available_input_routing_channels]
            except Exception:
                pass
            if hasattr(device, 'available_input_routing_types'):
                result["available_input_routing_types"] = [
                    {"display_name": str(r.display_name) if hasattr(r, 'display_name') else str(r)}
                    for r in device.available_input_routing_types
                ]
            return result
        except Exception as e:
            self.log_message("Error getting device sidechain: " + str(e))
            raise

    def _set_device_sidechain(self, track_index, device_index, routing_type_name, channel_name=None):
        """Set device sidechain/input routing by name, matching track input routing."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not hasattr(device, "input_routing_type"):
                raise Exception("Device '{0}' has no input_routing_type".format(device.name))
            for routing_type in device.available_input_routing_types:
                name = str(routing_type.display_name) if hasattr(routing_type, 'display_name') else str(routing_type)
                if name == routing_type_name:
                    device.input_routing_type = routing_type
                    chosen = None
                    try:
                        channels = list(device.available_input_routing_channels)
                        pick = channels[0] if channels else None
                        if channel_name:
                            want = str(channel_name).lower()
                            for c in channels:
                                if str(c.display_name).lower() == want:
                                    pick = c
                                    break
                            else:
                                raise Exception("no input channel %r; available: %s" % (
                                    channel_name, ", ".join(str(c.display_name) for c in channels)))
                        if pick is not None:
                            device.input_routing_channel = pick
                            chosen = str(pick.display_name)
                    except Exception as ce:
                        if channel_name:
                            raise
                        self.log_message("input channel not set: " + str(ce))
                    return {
                        "input_routing_type": routing_type_name,
                        "input_routing_channel": chosen,
                        "device_name": device.name
                    }
            raise Exception("Routing type not found: " + routing_type_name)
        except Exception as e:
            self.log_message("Error setting device sidechain: " + str(e))
            raise

    def _get_rack_chains(self, track_index, device_index):
        """List chains on a rack device."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not self._safe_getattr(device, "can_have_chains", False):
                raise Exception("Device '{0}' cannot have chains".format(device.name))
            chains = []
            for i, chain in enumerate(device.chains):
                vol = None
                mixer = self._safe_getattr(chain, "mixer_device", None)
                if mixer is not None:
                    vol_param = self._safe_getattr(mixer, "volume", None)
                    vol = self._safe_getattr(vol_param, "value", None)
                devices = self._safe_getattr(chain, "devices", [])
                try:
                    device_count = len(devices) if devices is not None else 0
                except Exception:
                    device_count = 0
                chains.append({
                    "index": i,
                    "name": self._safe_getattr(chain, "name", ""),
                    "mute": bool(self._safe_getattr(chain, "mute", False)),
                    "solo": bool(self._safe_getattr(chain, "solo", False)),
                    "volume": vol,
                    "device_count": device_count
                })
            return {
                "device_name": device.name,
                "chain_count": len(chains),
                "chains": chains
            }
        except Exception as e:
            self.log_message("Error getting rack chains: " + str(e))
            raise

    def _insert_rack_chain(self, track_index, device_index, index=-1, name=None):
        """Insert a chain on a rack (Live 12.3+ insert_chain)."""
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not hasattr(device, "insert_chain"):
                raise Exception("insert_chain requires Live 12.3+; load a multi-chain rack from the browser instead")
            insert_at = -1 if index is None else int(index)
            if insert_at < 0:
                insert_at = len(device.chains)
            device.insert_chain(insert_at)
            if name:
                device.chains[insert_at].name = name
            chain = device.chains[insert_at]
            return {
                "inserted": True,
                "index": insert_at,
                "name": self._safe_getattr(chain, "name", ""),
                "chain_count": len(device.chains)
            }
        except Exception as e:
            self.log_message("Error inserting rack chain: " + str(e))
            raise

    def _set_chain_mixer(self, track_index, device_index, chain_index, mute=None, solo=None, volume=None, panning=None):
        """Set mute/solo/volume/panning on a rack chain.

        volume and pan are 0-1 (pan 0=left, 1=right). Negative pan is accepted as -1..1.
        """
        try:
            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            device = track.devices[device_index]
            if not self._safe_getattr(device, "can_have_chains", False):
                raise Exception("Device '{0}' cannot have chains".format(device.name))
            if chain_index < 0 or chain_index >= len(device.chains):
                raise IndexError("Chain index out of range")
            chain = device.chains[chain_index]
            mixer = chain.mixer_device
            if mute is not None:
                chain.mute = bool(mute)
            if solo is not None:
                chain.solo = bool(solo)
            if volume is not None:
                volume = float(volume)
                if volume < 0.0 or volume > 1.0:
                    raise ValueError("Volume must be between 0.0 and 1.0")
                vol_param = mixer.volume
                vol_param.value = vol_param.min + volume * (vol_param.max - vol_param.min)
            if panning is not None:
                panning = self._normalized_panning(panning)
                pan_param = mixer.panning
                pan_param.value = pan_param.min + panning * (pan_param.max - pan_param.min)
            vol_out = None
            pan_out = None
            vol_param = self._safe_getattr(mixer, "volume", None)
            pan_param = self._safe_getattr(mixer, "panning", None)
            vol_out = self._safe_getattr(vol_param, "value", None)
            pan_out = self._safe_getattr(pan_param, "value", None)
            return {
                "device_name": device.name,
                "chain_index": chain_index,
                "name": self._safe_getattr(chain, "name", ""),
                "mute": bool(self._safe_getattr(chain, "mute", False)),
                "solo": bool(self._safe_getattr(chain, "solo", False)),
                "volume": vol_out,
                "panning": pan_out
            }
        except Exception as e:
            self.log_message("Error setting chain mixer: " + str(e))
            raise

    def _macro_number_from_name(self, original_name):
        text = str(original_name or "")
        if not text.startswith("Macro"):
            return None
        rest = text[5:].strip()
        if rest == "":
            return None
        try:
            return int(rest.split()[0])
        except (ValueError, TypeError):
            return None

    def _get_rack_device(self, track_index, device_index):
        track = self._get_track(track_index)
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        if not self._safe_getattr(device, "can_have_chains", False):
            raise Exception("Device '{0}' is not a rack".format(self._safe_getattr(device, "name", "")))
        return track, device

    def _rack_variation_count(self, device):
        count = self._safe_getattr(device, "variation_count", None)
        if count is not None:
            try:
                return int(count)
            except (TypeError, ValueError):
                pass
        variations = self._safe_getattr(device, "macro_variations", None)
        if variations is None:
            return None
        try:
            return len(variations)
        except TypeError:
            return None

    def _rack_macro_state(self, track_index, device_index, device):
        raw_mapped = self._safe_getattr(device, "macros_mapped", None)
        mapped_flags = None
        if raw_mapped is not None:
            if isinstance(raw_mapped, (list, tuple)):
                mapped_flags = [bool(value) for value in raw_mapped]
            else:
                try:
                    mapped_flags = [bool(value) for value in list(raw_mapped)]
                except (TypeError, ValueError):
                    if isinstance(raw_mapped, (bool,) + _INTEGER_TYPES):
                        mapped_flags = bool(raw_mapped)

        visible_count = self._safe_getattr(device, "visible_macro_count", None)
        macros = []
        for i, param in enumerate(self._safe_getattr(device, "parameters", [])):
            original = self._safe_getattr(param, "original_name", None)
            pname = self._safe_getattr(param, "name", "")
            ident = original if original not in (None, "") else pname
            ident = str(ident) if ident is not None else ""
            if not ident.startswith("Macro"):
                continue
            macro_number = self._macro_number_from_name(ident)
            if visible_count is not None and macro_number is not None:
                try:
                    if macro_number > int(visible_count):
                        continue
                except (TypeError, ValueError):
                    pass
            mapped = None
            if isinstance(mapped_flags, list) and macro_number is not None:
                mapped_index = macro_number - 1
                mapped = (mapped_index >= 0 and mapped_index < len(mapped_flags) and
                          mapped_flags[mapped_index])
            elif isinstance(mapped_flags, bool):
                mapped = mapped_flags
            macro = {
                "index": i,
                "name": pname,
                "original_name": ident,
                "value": self._safe_getattr(param, "value", None),
                "min": self._safe_getattr(param, "min", None),
                "max": self._safe_getattr(param, "max", None)
            }
            if mapped is not None:
                macro["mapped"] = mapped
            macros.append(macro)

        mapped_macros = [macro for macro in macros if macro.get("mapped") is True]
        result = {
            "track_index": track_index,
            "device_index": device_index,
            "device_name": self._safe_getattr(device, "name", ""),
            "visible_macro_count": visible_count,
            "variation_count": self._rack_variation_count(device),
            "selected_variation_index": self._safe_getattr(device, "selected_variation_index", None),
            "macros": macros,
            "mapped_macros": mapped_macros,
            "note": "mapping a param onto a macro is GUI-only"
        }
        if raw_mapped is not None:
            result["macros_mapped"] = mapped_flags
        return result

    def _get_rack_macros(self, track_index, device_index):
        """List rack Macro parameters (including renamed ones). Mapping a param onto a macro is GUI-only."""
        try:
            _, device = self._get_rack_device(track_index, device_index)
            return self._rack_macro_state(track_index, device_index, device)
        except Exception as e:
            self.log_message("Error getting rack macros: " + str(e))
            raise

    def _rack_mutation(self, track_index, device_index, method_name):
        _, device = self._get_rack_device(track_index, device_index)
        method = getattr(device, method_name, None)
        if method is None:
            raise Exception("{0} requires Live 12.3+".format(method_name))
        method()
        return self._rack_macro_state(track_index, device_index, device)

    def _add_macro(self, track_index, device_index):
        return self._rack_mutation(track_index, device_index, "add_macro")

    def _remove_macro(self, track_index, device_index):
        return self._rack_mutation(track_index, device_index, "remove_macro")

    def _randomize_macros(self, track_index, device_index):
        return self._rack_mutation(track_index, device_index, "randomize_macros")

    def _store_macro_variation(self, track_index, device_index):
        return self._rack_mutation(track_index, device_index, "store_variation")

    def _select_macro_variation(self, device, variation_index):
        count = self._rack_variation_count(device)
        if variation_index is None:
            raise ValueError("variation_index is required")
        variation_index = self._integer_value(variation_index, "variation_index")
        if variation_index < 0 or (count is not None and variation_index >= count):
            raise IndexError("Variation index out of range")
        if not hasattr(device, "selected_variation_index"):
            raise Exception("selected_variation_index is not available on this Live version")
        device.selected_variation_index = variation_index
        return variation_index

    def _recall_macro_variation(self, track_index, device_index, variation_index):
        _, device = self._get_rack_device(track_index, device_index)
        if not hasattr(device, "recall_selected_variation"):
            raise Exception("recall_selected_variation requires Live 12.3+")
        self._select_macro_variation(device, variation_index)
        device.recall_selected_variation()
        return self._rack_macro_state(track_index, device_index, device)

    def _delete_macro_variation(self, track_index, device_index, variation_index):
        _, device = self._get_rack_device(track_index, device_index)
        if not hasattr(device, "delete_selected_variation"):
            raise Exception("delete_selected_variation requires Live 12.3+")
        self._select_macro_variation(device, variation_index)
        device.delete_selected_variation()
        return self._rack_macro_state(track_index, device_index, device)

    def _get_simpler_device(self, track_index, device_index):
        track = self._get_track(track_index)
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        class_name = str(self._safe_getattr(device, "class_name", "") or "").lower()
        display_name = str(self._safe_getattr(device, "class_display_name", "") or "").lower()
        device_name = str(self._safe_getattr(device, "name", "") or "").lower()
        if class_name not in ("simpler", "originalsimpler") and display_name != "simpler" and device_name != "simpler":
            raise Exception("Device '{0}' is not a Simpler device".format(self._safe_getattr(device, "name", "")))
        if not hasattr(device, "sample"):
            raise Exception("Simpler sample is not available on this Live version")
        return track, device

    def _simpler_sample_state(self, track_index, device_index, track, device):
        sample = self._safe_getattr(device, "sample", None)
        if sample is None:
            raise Exception("Simpler has no sample loaded")
        start_marker = self._safe_getattr(sample, "start_marker", None)
        end_marker = self._safe_getattr(sample, "end_marker", None)
        return {
            "track_index": track_index,
            "track_name": self._safe_getattr(track, "name", ""),
            "device_index": device_index,
            "device_name": self._safe_getattr(device, "name", ""),
            "file_path": self._safe_getattr(sample, "file_path", None),
            "start_marker": int(start_marker) if start_marker is not None else None,
            "end_marker": int(end_marker) if end_marker is not None else None
        }

    def _get_simpler_sample(self, track_index, device_index):
        try:
            track, device = self._get_simpler_device(track_index, device_index)
            return self._simpler_sample_state(track_index, device_index, track, device)
        except Exception as e:
            self.log_message("Error getting Simpler sample: " + str(e))
            raise

    def _integer_value(self, value, name):
        if isinstance(value, bool):
            raise ValueError("{0} must be an integer".format(name))
        try:
            integer = int(value)
            if float(value) != float(integer):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError("{0} must be an integer".format(name))
        return integer

    def _sample_frame_value(self, value, name):
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("{0} must be an integer sample frame".format(name))
        try:
            frame = int(value)
            if float(value) != float(frame):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError("{0} must be an integer sample frame".format(name))
        if frame < 0:
            raise ValueError("{0} must be non-negative".format(name))
        return frame

    def _set_simpler_sample_window(self, track_index, device_index, start_marker=None, end_marker=None):
        try:
            track, device = self._get_simpler_device(track_index, device_index)
            sample = self._safe_getattr(device, "sample", None)
            if sample is None:
                raise Exception("Simpler has no sample loaded")
            start = self._sample_frame_value(start_marker, "start_marker")
            end = self._sample_frame_value(end_marker, "end_marker")
            current_start = self._sample_frame_value(
                self._safe_getattr(sample, "start_marker", None), "current start_marker")
            current_end = self._sample_frame_value(
                self._safe_getattr(sample, "end_marker", None), "current end_marker")
            new_start = current_start if start is None else start
            new_end = current_end if end is None else end
            if new_start is not None and new_end is not None and new_start > new_end:
                raise ValueError("start_marker cannot be after end_marker")
            if start is None and end is None:
                return self._simpler_sample_state(track_index, device_index, track, device)
            if not hasattr(sample, "start_marker") or not hasattr(sample, "end_marker"):
                raise Exception("Simpler sample markers are not available on this Live version")
            if new_end is not None and new_end < current_start:
                sample.start_marker = new_start
                sample.end_marker = new_end
            else:
                if end is not None:
                    sample.end_marker = new_end
                if start is not None:
                    sample.start_marker = new_start
            return self._simpler_sample_state(track_index, device_index, track, device)
        except Exception as e:
            self.log_message("Error setting Simpler sample window: " + str(e))
            raise

    def _replace_simpler_sample(self, track_index, device_index, file_path):
        try:
            track, device = self._get_simpler_device(track_index, device_index)
            if not isinstance(file_path, _STRING_TYPES) or not file_path.strip():
                raise ValueError("file_path is required")
            if not hasattr(device, "replace_sample"):
                raise Exception(
                    "replace_sample requires Live 12.4+; this Live build cannot replace a Simpler sample"
                )
            device.replace_sample(file_path)
            return self._simpler_sample_state(track_index, device_index, track, device)
        except Exception as e:
            self.log_message("Error replacing Simpler sample: " + str(e))
            raise

    def _get_application_info(self):
        try:
            app = self.application()
            if app is None:
                raise Exception("Could not access Live Application")
            result = {}
            for name in ("major_version", "minor_version", "bugfix_version"):
                value = self._safe_getattr(app, name, None)
                if value is not None:
                    result[name] = value
            version = self._safe_getattr(app, "version", None)
            if version is None:
                parts = [result.get(name) for name in ("major_version", "minor_version", "bugfix_version")]
                if all(part is not None for part in parts):
                    version = "{0}.{1}.{2}".format(parts[0], parts[1], parts[2])
            if version is not None:
                result["version"] = str(version)
            for name in ("current_dialog_message", "current_dialog_button_count", "open_dialog_count"):
                value = self._safe_getattr(app, name, None)
                if value is not None:
                    result[name] = value
            return result
        except Exception as e:
            self.log_message("Error getting application info: " + str(e))
            raise

    def _press_current_dialog_button(self, index):
        try:
            if index is None:
                raise ValueError("index is required")
            index = self._integer_value(index, "index")
            if index < 0:
                raise ValueError("index must be a non-negative integer")
            app = self.application()
            if app is None or not hasattr(app, "press_current_dialog_button"):
                raise Exception("press_current_dialog_button is not available on this Live version")
            count = self._safe_getattr(app, "current_dialog_button_count", None)
            if count is not None and index >= int(count):
                raise IndexError("Dialog button index out of range")
            app.press_current_dialog_button(index)
            result = {"pressed": True, "index": index}
            result.update(self._get_application_info())
            return result
        except Exception as e:
            self.log_message("Error pressing current dialog button: " + str(e))
            raise

    def _capture_and_insert_scene(self):
        """Capture currently playing clips into a new scene."""
        try:
            self._song.capture_and_insert_scene()
            return {"captured": True, "scene_count": len(self._song.scenes)}
        except Exception as e:
            self.log_message("Error capturing scene: " + str(e))
            raise

    def _set_clip_bounds_pair(self, clip, end_name, start_name, end_val, start_val):
        if hasattr(clip, end_name):
            try:
                setattr(clip, end_name, end_val)
                if hasattr(clip, start_name):
                    setattr(clip, start_name, start_val)
            except Exception:
                if hasattr(clip, start_name):
                    setattr(clip, start_name, start_val)
                setattr(clip, end_name, end_val)
        elif hasattr(clip, start_name):
            setattr(clip, start_name, start_val)

    def _crop_clip(self, track_index, clip_index, arrangement_clip_index=None):
        """Crop a clip to its loop, then reset loop/markers onto the cropped clip."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            clip.crop()
            length = float(clip.length)
            self._set_clip_bounds_pair(clip, "loop_end", "loop_start", length, 0.0)
            self._set_clip_bounds_pair(clip, "end_marker", "start_marker", length, 0.0)
            result = {
                "cropped": True,
                "length": clip.length,
                "loop_start": self._safe_getattr(clip, "loop_start", None),
                "loop_end": self._safe_getattr(clip, "loop_end", None),
                "start_marker": self._safe_getattr(clip, "start_marker", None),
                "end_marker": self._safe_getattr(clip, "end_marker", None)
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error cropping clip: " + str(e))
            raise

    def _set_clip_launch(self, track_index, clip_index, launch_mode=None, launch_quantization=None, legato=None, arrangement_clip_index=None):
        """Set clip launch_mode (0-3), launch_quantization, and/or legato."""
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            if launch_mode is not None:
                launch_mode = int(launch_mode)
                if launch_mode < 0 or launch_mode > 3:
                    raise ValueError("launch_mode must be 0-3")
                clip.launch_mode = launch_mode
            if launch_quantization is not None:
                clip.launch_quantization = launch_quantization
            if legato is not None:
                clip.legato = bool(legato)
            result = {
                "launch_mode": self._safe_getattr(clip, "launch_mode", None),
                "launch_quantization": self._safe_getattr(clip, "launch_quantization", None),
                "legato": self._safe_getattr(clip, "legato", None)
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip launch: " + str(e))
            raise

    def _get_cue_points(self):
        """List arrangement cue points."""
        try:
            cues = []
            for i, cue in enumerate(self._song.cue_points):
                cues.append({
                    "index": i,
                    "name": self._safe_getattr(cue, "name", ""),
                    "time": self._safe_getattr(cue, "time", None)
                })
            return {"cue_count": len(cues), "cue_points": cues}
        except Exception as e:
            self.log_message("Error getting cue points: " + str(e))
            raise

    def _toggle_cue(self):
        """Set or delete a cue at the current song time."""
        try:
            self._song.set_or_delete_cue()
            return {"cue_count": len(self._song.cue_points)}
        except Exception as e:
            self.log_message("Error toggling cue: " + str(e))
            raise

    def _jump_cue_object(self, cue):
        if hasattr(cue, "jump"):
            cue.jump()
        else:
            self._song.current_song_time = cue.time

    def _jump_to_cue(self, direction=None, index=None):
        """Jump to a cue by index, or to the next/prev cue relative to current time."""
        try:
            if isinstance(index, _INTEGER_TYPES):
                cues = self._song.cue_points
                if index < 0 or index >= len(cues):
                    raise IndexError("Cue index out of range")
                cue = cues[index]
                self._jump_cue_object(cue)
                return {
                    "jumped_to": index,
                    "name": self._safe_getattr(cue, "name", ""),
                    "time": self._safe_getattr(cue, "time", None)
                }
            if direction is not None:
                direction = str(direction).lower()
            now = float(self._song.current_song_time)
            best = None
            best_index = None
            best_time = None
            for i, cue in enumerate(self._song.cue_points):
                t = self._safe_getattr(cue, "time", None)
                if t is None:
                    continue
                t = float(t)
                if direction == "next":
                    if t > now and (best_time is None or t < best_time):
                        best, best_index, best_time = cue, i, t
                elif direction == "prev":
                    if t < now and (best_time is None or t > best_time):
                        best, best_index, best_time = cue, i, t
            if direction in ("next", "prev"):
                if best is None:
                    return {
                        "jumped": False,
                        "direction": direction,
                        "note": "No {0} cue".format(direction)
                    }
                self._jump_cue_object(best)
                return {
                    "jumped": True,
                    "direction": direction,
                    "index": best_index,
                    "name": self._safe_getattr(best, "name", ""),
                    "time": self._safe_getattr(best, "time", best_time)
                }
            raise Exception("Provide index (int) or direction ('next' or 'prev')")
        except Exception as e:
            self.log_message("Error jumping to cue: " + str(e))
            raise

    def _set_crossfader(self, value):
        """Set the master crossfader with a normalized 0-1 value."""
        try:
            value = float(value)
            if value < 0.0 or value > 1.0:
                raise ValueError("value must be between 0.0 and 1.0")
            cf = self._song.master_track.mixer_device.crossfader
            cf.value = cf.min + value * (cf.max - cf.min)
            return {"crossfader": cf.value, "normalized": value}
        except Exception as e:
            self.log_message("Error setting crossfader: " + str(e))
            raise

    def _set_crossfade_assign(self, track_index, assign):
        """Assign a track to crossfader A (0), none (1), or B (2)."""
        try:
            track = self._get_track(track_index)
            assign = int(assign)
            if assign not in (0, 1, 2):
                raise ValueError("assign must be 0 (A), 1 (none), or 2 (B)")
            track.mixer_device.crossfade_assign = assign
            return {
                "track_name": track.name,
                "crossfade_assign": track.mixer_device.crossfade_assign
            }
        except Exception as e:
            self.log_message("Error setting crossfade assign: " + str(e))
            raise

    def _show_view(self, view_name):
        """Show a Live view (Arranger, Session, Detail/Clip, Detail/DeviceChain, Browser)."""
        try:
            self.application().view.show_view(view_name)
            return {"view": view_name, "shown": True}
        except Exception as e:
            self.log_message("Error showing view: " + str(e))
            raise

    def _get_warp_markers(self, track_index, clip_index, arrangement_clip_index=None):
        """List warp markers on an audio clip."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            result = {"warping": self._safe_getattr(clip, "warping", None)}
            if hasattr(clip, "warp_markers"):
                markers = []
                for i, marker in enumerate(clip.warp_markers):
                    info = {"index": i}
                    if hasattr(marker, "beat_time"):
                        info["beat_time"] = marker.beat_time
                    if hasattr(marker, "sample_time"):
                        info["sample_time"] = marker.sample_time
                    markers.append(info)
                result["warp_markers"] = markers
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error getting warp markers: " + str(e))
            raise

    def _ensure_clip_warping(self, clip):
        if not self._safe_getattr(clip, "warping", False):
            clip.warping = True

    def _estimate_sample_time(self, clip, beat_time):
        """Sample seconds for beat_time: LOM conversion, then surrounding warp markers, then clip length."""
        if hasattr(clip, "beat_to_sample_time"):
            try:
                return float(clip.beat_to_sample_time(beat_time))
            except Exception:
                pass
        pairs = []
        markers = self._safe_getattr(clip, "warp_markers", None)
        if markers is not None:
            try:
                for marker in markers:
                    bt = self._safe_getattr(marker, "beat_time", None)
                    st = self._safe_getattr(marker, "sample_time", None)
                    if bt is not None and st is not None:
                        pairs.append((float(bt), float(st)))
            except Exception:
                pairs = []
        if len(pairs) >= 2:
            pairs.sort(key=lambda p: p[0])
            left = pairs[0]
            right = pairs[-1]
            for pair in pairs:
                if pair[0] <= beat_time:
                    left = pair
                if pair[0] >= beat_time:
                    right = pair
                    break
            span = right[0] - left[0]
            if span == 0:
                return left[1]
            frac = (beat_time - left[0]) / span
            return left[1] + frac * (right[1] - left[1])
        if len(pairs) == 1 and pairs[0][0] != 0:
            return pairs[0][1] * (beat_time / pairs[0][0])
        sample_length = self._safe_getattr(clip, "sample_length", None)
        sample_rate = self._safe_getattr(clip, "sample_rate", None)
        length = self._safe_getattr(clip, "length", None)
        if sample_length and sample_rate and length:
            seconds = float(sample_length) / float(sample_rate)
            return (float(beat_time) / float(length)) * seconds
        return None

    def _sample_time_as_seconds(self, clip, sample_time):
        """WarpMarker.sample_time is seconds. beat_to_sample_time often returns frames."""
        sample_time = float(sample_time)
        sample_rate = self._safe_getattr(clip, "sample_rate", None)
        sample_length = self._safe_getattr(clip, "sample_length", None)
        if not sample_rate:
            return sample_time
        sample_rate = float(sample_rate)
        length_sec = None
        if sample_length:
            length_sec = float(sample_length) / sample_rate
        if length_sec is not None and sample_time > length_sec * 1.5 and sample_time <= float(sample_length) * 1.01:
            return sample_time / sample_rate
        return sample_time

    def _make_warp_marker(self, clip, beat_time, sample_time):
        """Live.Clip.WarpMarker(sample_time_seconds, beat_time) — argument order is sample then beat."""
        errors = []
        if sample_time is None:
            sample_time = self._estimate_sample_time(clip, beat_time)
        if sample_time is None:
            return None, "could not determine sample_time"
        sample_time = self._sample_time_as_seconds(clip, sample_time)
        beat_time = float(beat_time)
        try:
            import Live
            WarpMarker = getattr(getattr(Live, "Clip", None), "WarpMarker", None)
            if WarpMarker is not None:
                try:
                    return WarpMarker(sample_time, beat_time), None
                except Exception as e1:
                    errors.append("WarpMarker(sample, beat): {0}".format(str(e1)))
                try:
                    return WarpMarker(beat_time, sample_time), None
                except Exception as e2:
                    errors.append("WarpMarker(beat, sample): {0}".format(str(e2)))
        except Exception as e:
            errors.append("import Live.Clip.WarpMarker: {0}".format(str(e)))
        try:
            markers = getattr(clip, "warp_markers", None)
            if markers is not None and len(markers) > 0:
                cls = type(markers[0])
                try:
                    return cls(sample_time, beat_time), None
                except Exception as e3:
                    errors.append("type(existing)(sample, beat): {0}".format(str(e3)))
                try:
                    return cls(beat_time, sample_time), None
                except Exception as e4:
                    errors.append("type(existing)(beat, sample): {0}".format(str(e4)))
        except Exception as e:
            errors.append("existing marker type: {0}".format(str(e)))
        return None, "; ".join(errors) if errors else "no WarpMarker constructor"

    def _add_warp_marker(self, track_index, clip_index, beat_time, sample_time=None, arrangement_clip_index=None):
        """Add a warp marker: Live.Clip.WarpMarker(sample_time seconds, beat_time)."""
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "add_warp_marker"):
                raise Exception("add_warp_marker is not supported on this Live version")
            self._ensure_clip_warping(clip)
            beat_time = float(beat_time)
            if sample_time is None and hasattr(clip, "beat_to_sample_time"):
                try:
                    sample_time = clip.beat_to_sample_time(beat_time)
                except Exception:
                    sample_time = None
            wm, make_err = self._make_warp_marker(clip, beat_time, sample_time)
            if wm is None:
                raise Exception("could not construct WarpMarker: {0}".format(make_err))
            clip.add_warp_marker(wm)
            used_sample = self._sample_time_as_seconds(clip, sample_time) if sample_time is not None else None
            result = {"added": True, "beat_time": beat_time, "sample_time": used_sample}
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error adding warp marker: " + str(e))
            raise

    def _move_warp_marker(self, track_index, clip_index, beat_time, beat_time_distance, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "move_warp_marker"):
                raise Exception("move_warp_marker is not supported on this Live version")
            beat_time = float(beat_time)
            beat_time_distance = float(beat_time_distance)
            clip.move_warp_marker(beat_time, beat_time_distance)
            result = {
                "moved": True,
                "beat_time": beat_time,
                "beat_time_distance": beat_time_distance
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error moving warp marker: " + str(e))
            raise

    def _delete_warp_marker(self, track_index, clip_index, beat_time, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "remove_warp_marker"):
                raise Exception("remove_warp_marker is not supported on this Live version")
            beat_time = float(beat_time)
            clip.remove_warp_marker(beat_time)
            result = {"deleted": True, "beat_time": beat_time}
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error deleting warp marker: " + str(e))
            raise

    def _convert_clip_time(self, track_index, clip_index, beat_time=None, sample_time=None, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            if beat_time is None and sample_time is None:
                raise Exception("Provide beat_time and/or sample_time")
            result = {}
            if beat_time is not None:
                beat_time = float(beat_time)
                result["beat_time"] = beat_time
                if not hasattr(clip, "beat_to_sample_time"):
                    raise Exception("beat_to_sample_time is not available on this clip")
                result["sample_time"] = clip.beat_to_sample_time(beat_time)
            if sample_time is not None:
                sample_time = float(sample_time)
                if not hasattr(clip, "sample_to_beat_time"):
                    raise Exception("sample_to_beat_time is not available on this clip")
                if beat_time is None:
                    result["sample_time"] = sample_time
                    result["beat_time"] = clip.sample_to_beat_time(sample_time)
                else:
                    result["sample_time_input"] = sample_time
                    result["beat_time_from_sample"] = clip.sample_to_beat_time(sample_time)
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error converting clip time: " + str(e))
            raise

    def _set_clip_color(self, track_index, clip_index, color_index=None, color=None, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            result = self._apply_color(clip, color_index, color)
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip color: " + str(e))
            raise

    def _set_clip_muted(self, track_index, clip_index, muted, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            clip.muted = bool(muted)
            result = {"muted": clip.muted}
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip muted: " + str(e))
            raise

    def _set_clip_markers(self, track_index, clip_index, start_marker=None, end_marker=None, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            if start_marker is None and end_marker is None:
                raise Exception("Provide start_marker and/or end_marker")
            cur_start = float(clip.start_marker)
            cur_end = float(clip.end_marker)
            new_start = float(start_marker) if start_marker is not None else cur_start
            new_end = float(end_marker) if end_marker is not None else cur_end
            if new_start > new_end:
                raise ValueError("start_marker cannot be after end_marker")
            if start_marker is not None and end_marker is None and new_start > cur_end:
                raise ValueError("start_marker would be after end_marker; pass end_marker too")
            if end_marker is not None and start_marker is None and new_end < cur_start:
                raise ValueError("end_marker would be before start_marker; pass start_marker too")
            if new_end > cur_end:
                clip.end_marker = new_end
            if start_marker is not None:
                clip.start_marker = new_start
            if end_marker is not None and new_end <= cur_end:
                clip.end_marker = new_end
            result = {
                "start_marker": clip.start_marker,
                "end_marker": clip.end_marker
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip markers: " + str(e))
            raise

    def _set_clip_signature(self, track_index, clip_index, numerator, denominator, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "signature_numerator"):
                raise Exception("Clip time signature is not available on this Live version")
            clip.signature_numerator = int(numerator)
            clip.signature_denominator = int(denominator)
            result = {
                "signature_numerator": clip.signature_numerator,
                "signature_denominator": clip.signature_denominator
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip signature: " + str(e))
            raise

    def _quantize_pitch(self, track_index, clip_index, pitch, grid, strength, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=True,
                                     arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "quantize_pitch"):
                raise Exception("quantize_pitch is not available on this Live version")
            clip.quantize_pitch(int(pitch), int(grid), float(strength))
            result = {
                "quantized": True,
                "pitch": int(pitch),
                "grid": int(grid),
                "strength": float(strength)
            }
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error quantizing pitch: " + str(e))
            raise

    def _set_clip_ram_mode(self, track_index, clip_index, ram_mode, arrangement_clip_index=None):
        try:
            clip = self._session_clip(track_index, clip_index, midi=False,
                                     arrangement_clip_index=arrangement_clip_index)
            if not hasattr(clip, "ram_mode"):
                raise Exception("ram_mode is not available on this clip")
            clip.ram_mode = bool(ram_mode)
            result = {"ram_mode": clip.ram_mode}
            if arrangement_clip_index is not None:
                result["arrangement_clip_index"] = arrangement_clip_index
            return result
        except Exception as e:
            self.log_message("Error setting clip ram mode: " + str(e))
            raise

    def _tap_tempo(self):
        try:
            self._song.tap_tempo()
            return {"tapped": True, "tempo": self._song.tempo}
        except Exception as e:
            self.log_message("Error tapping tempo: " + str(e))
            raise

    def _jump_by(self, beats):
        try:
            beats = float(beats)
            intended = float(self._song.current_song_time) + beats
            self._song.jump_by(beats)
            return {"jumped": True, "beats": beats, "time": intended}
        except Exception as e:
            self.log_message("Error jumping by beats: " + str(e))
            raise

    def _continue_playing(self):
        try:
            self._song.continue_playing()
            return {"playing": bool(self._song.is_playing)}
        except Exception as e:
            self.log_message("Error continuing playback: " + str(e))
            raise

    def _set_session_record(self, on):
        try:
            self._song.session_record = bool(on)
            return {"session_record": bool(self._song.session_record)}
        except Exception as e:
            self.log_message("Error setting session record: " + str(e))
            raise

    def _set_session_automation_record(self, on):
        try:
            self._song.session_automation_record = bool(on)
            return {"session_automation_record": bool(self._song.session_automation_record)}
        except Exception as e:
            self.log_message("Error setting session automation record: " + str(e))
            raise

    def _re_enable_automation(self):
        try:
            self._song.re_enable_automation()
            return {"re_enabled": True}
        except Exception as e:
            self.log_message("Error re-enabling automation: " + str(e))
            raise

    def _set_count_in_duration(self, bars):
        try:
            if not hasattr(self._song, "count_in_duration"):
                raise Exception("count_in_duration is not available on this Live version")
            self._song.count_in_duration = int(bars)
            return {"count_in_duration": self._song.count_in_duration}
        except Exception as e:
            self.log_message("Error setting count-in duration: " + str(e))
            raise

    def _set_exclusive_arm(self, on):
        try:
            if not hasattr(self._song, "exclusive_arm"):
                raise Exception("exclusive_arm is not available on this Live version")
            self._song.exclusive_arm = bool(on)
            return {"exclusive_arm": bool(self._song.exclusive_arm)}
        except Exception as e:
            self.log_message("Error setting exclusive arm: " + str(e))
            raise

    def _set_punch(self, punch_in=None, punch_out=None):
        try:
            if punch_in is None and punch_out is None:
                raise Exception("Provide punch_in and/or punch_out")
            if punch_in is not None:
                self._song.punch_in = bool(punch_in)
            if punch_out is not None:
                self._song.punch_out = bool(punch_out)
            return {
                "punch_in": bool(self._safe_getattr(self._song, "punch_in", False)),
                "punch_out": bool(self._safe_getattr(self._song, "punch_out", False))
            }
        except Exception as e:
            self.log_message("Error setting punch: " + str(e))
            raise

    def _set_song_scale(self, scale_name=None, root_note=None):
        try:
            if scale_name is None and root_note is None:
                raise Exception("Provide scale_name and/or root_note")
            if scale_name is not None and hasattr(self._song, "scale_name"):
                self._song.scale_name = scale_name
            if root_note is not None and hasattr(self._song, "root_note"):
                self._song.root_note = int(root_note)
            result = {}
            if hasattr(self._song, "scale_name"):
                result["scale_name"] = self._song.scale_name
            if hasattr(self._song, "root_note"):
                result["root_note"] = self._song.root_note
            return result
        except Exception as e:
            self.log_message("Error setting song scale: " + str(e))
            raise

    def _set_track_color(self, track_index, color_index=None, color=None):
        try:
            track = self._get_track(track_index)
            result = self._apply_color(track, color_index, color)
            result["track_index"] = track_index
            result["name"] = self._safe_getattr(track, "name", "")
            return result
        except Exception as e:
            self.log_message("Error setting track color: " + str(e))
            raise

    def _set_scene_color(self, scene_index, color_index=None, color=None):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene = self._song.scenes[scene_index]
            result = self._apply_color(scene, color_index, color)
            result["scene_index"] = scene_index
            result["name"] = self._safe_getattr(scene, "name", "")
            return result
        except Exception as e:
            self.log_message("Error setting scene color: " + str(e))
            raise

    def _duplicate_scene(self, index):
        try:
            index = int(index)
            if index < 0 or index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            self._song.duplicate_scene(index)
            return {"duplicated": True, "index": index, "scene_count": len(self._song.scenes)}
        except Exception as e:
            self.log_message("Error duplicating scene: " + str(e))
            raise

    def _set_scene_tempo(self, scene_index, tempo=None):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene = self._song.scenes[scene_index]
            if tempo is not None:
                if hasattr(scene, "tempo"):
                    scene.tempo = float(tempo)
                elif not hasattr(scene, "tempo_enabled"):
                    raise Exception("Scene tempo is not available on this Live version")
                if hasattr(scene, "tempo_enabled"):
                    scene.tempo_enabled = True
            result = {
                "scene_index": scene_index,
                "tempo": self._safe_getattr(scene, "tempo", None),
                "tempo_enabled": self._safe_getattr(scene, "tempo_enabled", None)
            }
            return result
        except Exception as e:
            self.log_message("Error setting scene tempo: " + str(e))
            raise

    def _set_scene_signature(self, scene_index, numerator, denominator):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene = self._song.scenes[scene_index]
            num_attr = None
            den_attr = None
            if hasattr(scene, "signature_numerator"):
                num_attr, den_attr = "signature_numerator", "signature_denominator"
            elif hasattr(scene, "time_signature_numerator"):
                num_attr, den_attr = "time_signature_numerator", "time_signature_denominator"
            if num_attr is None:
                raise Exception("Scene time signature is not available on this Live version")
            setattr(scene, num_attr, int(numerator))
            setattr(scene, den_attr, int(denominator))
            result = {
                "scene_index": scene_index,
                "numerator": getattr(scene, num_attr),
                "denominator": getattr(scene, den_attr)
            }
            return result
        except Exception as e:
            self.log_message("Error setting scene signature: " + str(e))
            raise

    def _set_cue_volume(self, value):
        try:
            value = float(value)
            if value < 0.0 or value > 1.0:
                raise ValueError("value must be between 0.0 and 1.0")
            mixer = self._song.master_track.mixer_device
            if not hasattr(mixer, "cue_volume"):
                raise Exception("cue_volume is not available on this Live version")
            cv = mixer.cue_volume
            cv.value = cv.min + value * (cv.max - cv.min)
            return {"cue_volume": cv.value, "normalized": value}
        except Exception as e:
            self.log_message("Error setting cue volume: " + str(e))
            raise
