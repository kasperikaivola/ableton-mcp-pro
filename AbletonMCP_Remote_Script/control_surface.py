from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import json
import socket
import threading
import time
import traceback

try:
    from .mixins import (
        ArrangementMixin,
        BrowserMixin,
        ClipDetailMixin,
        ClipsNotesMixin,
        DevicesBrowserMixin,
        RacksRoutingMixin,
        SessionMixin,
        SimplerMixin,
        TransportMixerMixin,
        WarpDetailMixin,
    )
    from .support import DEFAULT_PORT, HOST, queue
except (ImportError, ValueError):
    from mixins import (
        ArrangementMixin,
        BrowserMixin,
        ClipDetailMixin,
        ClipsNotesMixin,
        DevicesBrowserMixin,
        RacksRoutingMixin,
        SessionMixin,
        SimplerMixin,
        TransportMixerMixin,
        WarpDetailMixin,
    )
    from support import DEFAULT_PORT, HOST, queue


class AbletonMCP(
        SessionMixin,
        ArrangementMixin,
        ClipsNotesMixin,
        ClipDetailMixin,
        DevicesBrowserMixin,
        BrowserMixin,
        RacksRoutingMixin,
        SimplerMixin,
        TransportMixerMixin,
        WarpDetailMixin,
        ControlSurface):
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

                        # The Live object model is main-thread-affine. The two
                        # real-time recording commands retain their worker-thread
                        # implementations and marshal their own individual steps.
                        if command.get("type") in ("record_arrangement", "resample_master"):
                            response = self._process_command(command)
                        else:
                            response = self._run_on_main_thread(
                                lambda: self._process_command(command, on_main_thread=True)
                            )

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

    def _run_on_main_thread(self, operation, timeout=9.0):
        """Run one ordinary command on Live's main thread with a bounded wait."""
        response_queue = queue.Queue()

        def task():
            try:
                response_queue.put((True, operation()))
            except Exception as e:
                response_queue.put((False, e))

        self.schedule_message(0, task)
        try:
            succeeded, value = response_queue.get(timeout=timeout)
        except queue.Empty:
            raise Exception("Timeout waiting for Live's main thread")
        if not succeeded:
            raise value
        return value

    def _process_command(self, command, on_main_thread=False):
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
            elif command_type in ["get_application_info",
                                 "create_midi_track", "set_track_name",
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
                                 "load_drum_pad_sample",
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
                        if command_type == "get_application_info":
                            result = self._get_application_info()
                        elif command_type == "create_midi_track":
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
                        elif command_type == "load_drum_pad_sample":
                            result = self._load_drum_pad_sample(
                                params.get("track_index", 0), params.get("device_index", 0),
                                params.get("note"), params.get("file_path", ""), params.get("name"))
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
                if on_main_thread:
                    main_thread_task()
                else:
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
