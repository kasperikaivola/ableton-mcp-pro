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

class RacksRoutingMixin(object):
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
