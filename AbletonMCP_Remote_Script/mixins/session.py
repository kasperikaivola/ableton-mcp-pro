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

class SessionMixin(object):
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
