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

class ClipsNotesMixin(object):
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

    def _clip_native_notes(self, clip):
        if not hasattr(clip, "get_notes_extended"):
            raise Exception("get_notes_extended is required for note IDs")
        return clip.get_notes_extended(from_pitch=0, pitch_span=128,
                                       from_time=0, time_span=clip.length)

    def _clip_note_dicts(self, clip):
        return [self._note_dict(note) for note in self._clip_native_notes(clip)]

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
            native_notes = self._clip_native_notes(clip)
            by_id = {}
            for note in native_notes:
                note_id = self._safe_getattr(note, "note_id", None)
                if note_id is not None:
                    by_id[note_id] = note
            editable_fields = (
                "pitch", "start_time", "duration", "velocity", "mute",
                "probability", "velocity_deviation", "release_velocity"
            )
            modified_notes = []
            for patch in notes:
                if not isinstance(patch, dict):
                    raise ValueError("each note modification must be a dictionary")
                if "note_id" not in patch or patch.get("note_id") is None:
                    raise ValueError("each note modification must include note_id")
                note_id = patch.get("note_id")
                if note_id not in by_id:
                    raise ValueError("note_id {0} was not found in the clip".format(note_id))
                native_note = by_id[note_id]
                for name, value in patch.items():
                    if name == "note_id":
                        continue
                    if name not in editable_fields:
                        raise ValueError("unsupported note property: {0}".format(name))
                    setattr(native_note, name, value)
                modified_notes.append(native_note)
            if modified_notes:
                # Boost.Python requires the native MidiNoteVector returned by
                # get_notes_extended; a normal Python list is rejected.
                clip.apply_note_modifications(native_notes)
            full_notes = [self._note_dict(note) for note in modified_notes]
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
