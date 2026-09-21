from __future__ import absolute_import, print_function, unicode_literals

import threading
import traceback

try:
    from ..support import (
    _ARRANGEMENT_ENVELOPE_NOTE,
    _INTEGER_TYPES,
    _MOVE_DEVICE_INSTRUMENT_MSG,
    _STRING_TYPES,
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
    from support import (
    _ARRANGEMENT_ENVELOPE_NOTE,
    _INTEGER_TYPES,
    _MOVE_DEVICE_INSTRUMENT_MSG,
    _STRING_TYPES,
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

class ArrangementMixin(object):
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

    def _capture_and_insert_scene(self):
        """Capture currently playing clips into a new scene."""
        try:
            self._song.capture_and_insert_scene()
            return {"captured": True, "scene_count": len(self._song.scenes)}
        except Exception as e:
            self.log_message("Error capturing scene: " + str(e))
            raise
