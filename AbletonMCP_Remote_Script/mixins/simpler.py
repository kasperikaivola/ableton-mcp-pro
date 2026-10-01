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

class SimplerMixin(object):
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

    def _load_drum_pad_sample(self, track_index, device_index, note, file_path, name=None):
        """Create one Drum Rack chain, insert Simpler, and load a sample (Live 12.4+)."""
        try:
            note = self._integer_value(note, "note")
            if note < 0 or note > 127:
                raise ValueError("note must be between 0 and 127")
            if not isinstance(file_path, _STRING_TYPES) or not file_path.strip():
                raise ValueError("file_path is required")

            app = self.application()
            major = int(app.get_major_version())
            minor = int(app.get_minor_version())
            if major < 12 or (major == 12 and minor < 4):
                raise Exception("load_drum_pad_sample requires Live 12.4+ (Simpler.replace_sample)")

            track = self._get_track(track_index)
            if device_index < 0 or device_index >= len(track.devices):
                raise IndexError("Device index out of range")
            rack = track.devices[device_index]
            if not bool(self._safe_getattr(rack, "can_have_drum_pads", False)):
                raise Exception("Device '{0}' is not a top-level Drum Rack".format(
                    self._safe_getattr(rack, "name", "")))
            if not hasattr(rack, "insert_chain"):
                raise Exception("load_drum_pad_sample requires Live 12.4+ rack chain insertion")

            target_pad = None
            for pad in rack.drum_pads:
                if int(pad.note) == note:
                    target_pad = pad
                    break
            if target_pad is None:
                raise Exception("Drum Rack has no pad for MIDI note {0}".format(note))
            if len(target_pad.chains):
                raise Exception("Drum Rack pad {0} is not empty".format(note))

            chain_index = len(rack.chains)
            try:
                rack.insert_chain(chain_index)
                chain = rack.chains[chain_index]
                if not hasattr(chain, "in_note"):
                    raise Exception("DrumChain.in_note is unavailable")
                chain.in_note = note
                if name:
                    chain.name = name
                if not hasattr(chain, "insert_device"):
                    raise Exception("DrumChain.insert_device is unavailable")
                chain.insert_device("Simpler")
                simpler = chain.devices[-1]
                if not hasattr(simpler, "replace_sample"):
                    raise Exception("Simpler.replace_sample is unavailable")
                simpler.replace_sample(file_path)
                return {
                    "track_index": track_index,
                    "device_index": device_index,
                    "rack_name": self._safe_getattr(rack, "name", ""),
                    "note": note,
                    "pad_name": self._safe_getattr(target_pad, "name", ""),
                    "chain_index": chain_index,
                    "chain_name": self._safe_getattr(chain, "name", ""),
                    "file_path": file_path,
                    "loaded": True,
                }
            except Exception:
                # The pad was verified empty, so this removes only the partial
                # chain created by this operation.
                try:
                    target_pad.delete_all_chains()
                except Exception:
                    pass
                raise
        except Exception as e:
            self.log_message("Error loading Drum Rack pad sample: " + str(e))
            raise
