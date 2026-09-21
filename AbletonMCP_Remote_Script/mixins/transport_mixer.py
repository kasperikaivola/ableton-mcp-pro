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

class TransportMixerMixin(object):
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
