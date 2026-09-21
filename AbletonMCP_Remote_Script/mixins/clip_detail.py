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

class ClipDetailMixin(object):
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
