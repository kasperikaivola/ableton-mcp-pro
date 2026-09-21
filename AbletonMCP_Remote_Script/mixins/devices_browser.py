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


class DevicesBrowserMixin(object):
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
