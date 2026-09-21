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

class WarpDetailMixin(object):
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
