import json
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

from ..runtime import get_ableton_connection, logger, mcp


_MANUAL_SETTINGS_HANDOFF = (
    "For new Serum 2 sounds, missing Configure controls do not block offline preset "
    "creation: read get_synth_sound_design_guide(synth='serum-presets', "
    "section='workflow'), then new-preset-design and module-editing. Design and write "
    "a separate .SerumPreset covering sources, filters, envelopes, modulation, FX "
    "and voicing; distinguish written file state from loaded-instance state. "
    "Group verified output-file settings as encoded in output; not loaded, with "
    "a load/verification step instead of redundant manual recreation. "
    "For existing Serum transformations such as make it faster/darker/bouncy, "
    "read serum-presets/existing-preset-edits: unpack the current exported preset "
    "to complete JSON, edit separate JSON and repack a separate preset. Preserve "
    "the original and unrelated state; a library file may omit unsaved changes. "
    "When designing/editing this plug-in, always list every intended setting not applied "
    "through MCP in the final chat, grouped by track and device. For Serum 2, include a "
    "'Serum 2 — manual settings' section covering wavetable selections, FX bus/order and "
    "values, and other missing controls/modulation. Give exact desired UI values/selections "
    "and units, labelled 'not applied — set manually'. These are instructions, not a "
    "readback of current unmapped values. For Omnisphere include an 'Omnisphere — manual "
    "settings' section with version, Part, Layer and FX rack identity. Read "
    "get_synth_sound_design_guide for Serum 2/Omnisphere workflows, controls and recipes "
    "before designing a patch or suggesting improvements. Suggestions alone do not "
    "authorize edits. Compare the intended patch with this instance's "
    "unfiltered configured inventory; do not assume every wavetable/FX control is missing. "
    "Do not guess opaque host labels or claim wavetable position selects a table. Mark "
    "unverifiable names/values unknown, and distinguish proposed choices from readback. "
    "Describe any inaccessible time-varying automation separately; a static manual value "
    "does not implement it. If all intended changes were verified, explicitly say no manual "
    "settings are required."
)

@mcp.tool()
def get_device_parameters(
    ctx: Context,
    track_index: int,
    device_index: int,
    query: str = None,
    include_host_names: bool = False,
) -> str:
    """
    Get parameters of a device on a track (Live devices and configured VST/AU knobs).

    Values are normalized 0.0–1.0. For plug-ins (Serum 2, etc.) only
    parameters in Live's Configure panel appear here (about 128 max). Live does
    not group those sliders; this tool adds inferred `groups` from names
    (Oscillator A/B/C, Filter 1, Envelope 1, Macros, …). Use query="Oscillator A"
    or query="Filter 1" to fetch one group.

    There is no LOM command to auto-add every host-automatable knob. After
    Configure, save Default Configuration or an .adg rack so new instances keep
    the list.

    Agent handoff: for EVERY Serum 2 patch design/edit, read this instance's
    unfiltered inventory and include a 'Serum 2 — manual settings' section in
    the final chat. List all intended but unapplied wavetable, FX, modulation,
    and other settings with UI locations, exact desired values/units and
    'not applied — set manually' status. Do not guess opaque host FX labels or
    equate wavetable position with table selection. Unknown values stay unknown;
    static manual values do not implement time-varying automation. State none
    required only when the intended changes were verified.

    For Serum 2 / Omnisphere sound design and improvement ideas, first read
    get_synth_sound_design_guide. Omnisphere requires an equivalent final-chat
    manual-settings handoff identifying version, Part, Layer and FX rack.
    For new Serum presets use the offline serum-presets creation workflow for
    settings missing here; actually generate the file, then report loading status.

    Parameters:
    - track_index: Track index (-1 master, -2/-3 returns)
    - device_index: Device index on the track
    - query: Optional filter on name, display_value, or group (e.g. "Filter 1", "Macro")
    - include_host_names: If true, also list PluginDevice.get_parameter_names()
      (names the plug-in reports; still not settable until Configured)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "include_host_names": include_host_names,
        }
        if query:
            payload["query"] = query
        result = ableton.send_command("get_device_parameters", payload)
        if result.get("is_plugin") or result.get("class_name") in ("PluginDevice", "AuPluginDevice"):
            result = dict(result)
            result["manual_settings_handoff"] = _MANUAL_SETTINGS_HANDOFF
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device parameters: {str(e)}")
        return f"Error getting device parameters: {str(e)}"

@mcp.tool()
def set_device_parameter(
    ctx: Context,
    track_index: int,
    device_index: int,
    value: float,
    parameter_index: int = None,
    parameter_name: str = None,
) -> str:
    """
    Set a device parameter using a normalized value (0.0 to 1.0).
    Prefer parameter_name for VSTs ("Filter 1 Freq", "Macro 1"). Do not reuse
    parameter_index across instances — Configure mappings differ and indices move.
    Missing names mean that knob is not in this instance's Configure panel.

    For Serum 2, always include intended but unapplied controls in the final
    chat's 'Serum 2 — manual settings' section with explicit UI values/units.
    Keep verified writes separate; a failed write is not an applied setting.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    - value: Normalized value between 0.0 and 1.0
    - parameter_index: Optional parameter index (from get_device_parameters)
    - parameter_name: Optional parameter name (case-insensitive; unique substring ok)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "value": value,
        }
        if parameter_index is not None:
            payload["parameter_index"] = parameter_index
        if parameter_name:
            payload["parameter_name"] = parameter_name
        result = ableton.send_command("set_device_parameter", payload)
        param_name = result.get("parameter_name", "unknown")
        actual_value = result.get("value", value)
        display = result.get("display_value")
        extra = f" ({display})" if display not in (None, "") else ""
        return f"Set '{param_name}' to {actual_value}{extra} (normalized: {value})"
    except Exception as e:
        logger.error(f"Error setting device parameter: {str(e)}")
        return f"Error setting device parameter: {str(e)}"

@mcp.tool()
def batch_set_device_parameters(
    ctx: Context,
    track_index: int,
    device_index: int,
    values: List[float],
    parameter_indices: List[int] = None,
    parameter_names: List[str] = None,
) -> str:
    """
    Set multiple device parameters at once using normalized values (0.0 to 1.0).
    Pass parameter_names (preferred for VSTs) or parameter_indices.

    For Serum 2, always include a 'Serum 2 — manual settings' section in the
    final chat: exact intended UI values/units for all missing/skipped controls,
    wavetable selections, FX and modulation. Do not report skipped values as
    applied or guess the semantic meaning of opaque host FX labels.

    Parameters:
    - track_index: The index of the track containing the device
    - device_index: The index of the device on the track
    - values: List of normalized values (0.0 to 1.0)
    - parameter_indices: Optional list of parameter indices
    - parameter_names: Optional list of parameter names (same length as values)
    """
    try:
        ableton = get_ableton_connection()
        payload = {
            "track_index": track_index,
            "device_index": device_index,
            "values": values,
        }
        if parameter_indices is not None:
            payload["parameter_indices"] = parameter_indices
        if parameter_names is not None:
            payload["parameter_names"] = parameter_names
        result = ableton.send_command("batch_set_device_parameters", payload)
        updated_count = result.get("updated_count", 0)
        skipped = result.get("skipped") or []
        params = result.get("parameters", [])
        details = ", ".join([f"{p['name']}={p['value']:.2f}" for p in params])
        msg = f"Updated {updated_count} parameters: {details}" if details else f"Updated {updated_count} parameters"
        if skipped:
            miss = ", ".join(str(s.get("name")) for s in skipped)
            msg += f". Skipped {len(skipped)} not configured on this instance: {miss}"
            msg += ". Include these unapplied settings and their intended UI values/units in the final chat's manual-settings handoff."
        return msg
    except Exception as e:
        logger.error(f"Error batch setting device parameters: {str(e)}")
        return f"Error batch setting device parameters: {str(e)}"

@mcp.tool()
def set_plugin_preset(
    ctx: Context,
    track_index: int,
    device_index: int,
    preset_index: int = None,
    preset_name: str = None,
) -> str:
    """
    Select a VST/AU host program-bank preset (PluginDevice.selected_preset_index).

    This is NOT Serum .serumpreset files. VST3 instruments often expose an empty
    bank. Use get_device_parameters to see `presets`.
    """
    try:
        ableton = get_ableton_connection()
        payload = {"track_index": track_index, "device_index": device_index}
        if preset_index is not None:
            payload["preset_index"] = preset_index
        if preset_name:
            payload["preset_name"] = preset_name
        result = ableton.send_command("set_plugin_preset", payload)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting plugin preset: {str(e)}")
        return f"Error setting plugin preset: {str(e)}"

@mcp.tool()
def insert_device(
    ctx: Context,
    track_index: int,
    device_name: str,
    target_index: Optional[int] = None,
) -> str:
    """Insert a native Live device by name at an optional device index.

    Requires Live 12.3+ and Track.insert_device. VST/AU and Max devices remain
    browser/.adg workflows; track_index preserves -1 master and -2/-3 return semantics.
    """
    try:
        params = {
            "track_index": track_index,
            "device_name": device_name,
        }
        if target_index is not None:
            params["target_index"] = target_index
        result = get_ableton_connection().send_command("insert_device", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error inserting device: {str(e)}")
        return f"Error inserting device: {str(e)}"

@mcp.tool()
def load_instrument_or_effect(ctx: Context, track_index: int, uri: str, clip_index: int = -1) -> str:
    """
    Load an instrument or effect onto a track using its URI.
    Use track_index -1 for the master track.

    MIDI effects (Chord, Scale, Arpeggiator) load via get_browser_items_at_path("midi_effects")
    then this tool; Live inserts MIDI FX before the instrument. Use move_device only to
    reorder MIDI effects among themselves or audio effects — Live cannot place an
    instrument before MIDI effects.

    Parameters:
    - track_index: The index of the track to load on (-1 for master)
    - uri: The URI of the instrument or effect to load (e.g., 'query:Synths#Instrument%20Rack:Bass:FileId_5116')
    - clip_index: Optional clip slot index to select before loading (needed for .alc audio clips). Default -1 means no clip slot selection.
    """
    try:
        ableton = get_ableton_connection()
        cmd_params = {
            "track_index": track_index,
            "item_uri": uri
        }
        if clip_index >= 0:
            cmd_params["clip_index"] = clip_index
        result = ableton.send_command("load_browser_item", cmd_params)
        
        # Browser loads are asynchronous from Live's device-list update. Report
        # only what the backend observed instead of presenting an empty list as
        # a verified post-load inventory.
        if result.get("loaded", False):
            item_name = result.get("item_name", uri)
            track_name = result.get("track_name", str(track_index))
            return (
                f"Live accepted browser item '{item_name}' on track '{track_name}'. "
                "Use get_track_info to verify the resulting device list."
            )
        else:
            return f"Failed to load instrument with URI '{uri}'"
    except Exception as e:
        logger.error(f"Error loading instrument by URI: {str(e)}")
        return f"Error loading instrument by URI: {str(e)}"

@mcp.tool()
def get_browser_tree(ctx: Context, category_type: str = "all") -> str:
    """
    Get a hierarchical tree of browser categories from Ableton.
    
    Parameters:
    - category_type: Type of categories to get ('all', 'instruments', 'sounds', 'drums',
                     'audio_effects', 'midi_effects', 'user_folders').
                     user_folders lists Places roots (e.g. user_folders/AudioAssets).
                     Remote Script only — the Max for Live backend does not expose Places.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_tree", {
            "category_type": category_type
        })
        
        # Check if we got any categories
        if "available_categories" in result and len(result.get("categories", [])) == 0:
            available_cats = result.get("available_categories", [])
            return (f"No categories found for '{category_type}'. "
                   f"Available browser categories: {', '.join(available_cats)}")
        
        # Format the tree in a more readable way
        total_folders = result.get("total_folders", 0)
        formatted_output = f"Browser tree for '{category_type}' (showing {total_folders} folders):\n\n"
        
        def format_tree(item, indent=0):
            output = ""
            if item:
                prefix = "  " * indent
                name = item.get("name", "Unknown")
                path = item.get("path", "")
                has_more = item.get("has_more", False)
                
                # Add this item
                output += f"{prefix}• {name}"
                if path:
                    output += f" (path: {path})"
                if has_more:
                    output += " [...]"
                output += "\n"
                
                # Add children
                for child in item.get("children", []):
                    output += format_tree(child, indent + 1)
            return output
        
        # Format each category
        for category in result.get("categories", []):
            formatted_output += format_tree(category)
            formatted_output += "\n"
        
        return formatted_output
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        else:
            logger.error(f"Error getting browser tree: {error_msg}")
            return f"Error getting browser tree: {error_msg}"

@mcp.tool()
def get_browser_items_at_path(ctx: Context, path: str) -> str:
    """
    Get browser items at a specific path in Ableton's browser.
    
    Parameters:
    - path: Path in the format "category/folder/subfolder"
            where category is one of the available browser categories in Ableton.
            user_folders lists Places roots (e.g. user_folders/AudioAssets).
            Remote Script only.
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("get_browser_items_at_path", {
            "path": path
        })
        
        # Check if there was an error with available categories
        if "error" in result and "available_categories" in result:
            error = result.get("error", "")
            available_cats = result.get("available_categories", [])
            return (f"Error: {error}\n"
                   f"Available browser categories: {', '.join(available_cats)}")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "Browser is not available" in error_msg:
            logger.error(f"Browser is not available in Ableton: {error_msg}")
            return f"Error: The Ableton browser is not available. Make sure Ableton Live is fully loaded and try again."
        elif "Could not access Live application" in error_msg:
            logger.error(f"Could not access Live application: {error_msg}")
            return f"Error: Could not access the Ableton Live application. Make sure Ableton Live is running and the Remote Script is loaded."
        elif "Unknown or unavailable category" in error_msg:
            logger.error(f"Invalid browser category: {error_msg}")
            return f"Error: {error_msg}. Please check the available categories using get_browser_tree."
        elif "Path part" in error_msg and "not found" in error_msg:
            logger.error(f"Path not found: {error_msg}")
            return f"Error: {error_msg}. Please check the path and try again."
        else:
            logger.error(f"Error getting browser items at path: {error_msg}")
            return f"Error getting browser items at path: {error_msg}"

@mcp.tool()
def load_drum_kit(ctx: Context, track_index: int, rack_uri: str, kit_path: str) -> str:
    """
    Load a drum rack and then load a specific drum kit into it.
    
    Parameters:
    - track_index: The index of the track to load on
    - rack_uri: The URI of the drum rack to load (e.g., 'Drums/Drum Rack')
    - kit_path: Path to the drum kit inside the browser (e.g., 'drums/acoustic/kit1')
    """
    try:
        ableton = get_ableton_connection()
        
        # Step 1: Load the drum rack
        result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": rack_uri
        })
        
        if not result.get("loaded", False):
            return f"Failed to load drum rack with URI '{rack_uri}'"
        
        # Step 2: Get the drum kit items at the specified path
        kit_result = ableton.send_command("get_browser_items_at_path", {
            "path": kit_path
        })
        
        if "error" in kit_result:
            return f"Loaded drum rack but failed to find drum kit: {kit_result.get('error')}"
        
        # Step 3: Find a loadable drum kit
        kit_items = kit_result.get("items", [])
        loadable_kits = [item for item in kit_items if item.get("is_loadable", False)]
        
        if not loadable_kits:
            return f"Loaded drum rack but no loadable drum kits found at '{kit_path}'"
        
        # Step 4: Load the first loadable kit
        kit_uri = loadable_kits[0].get("uri")
        load_result = ableton.send_command("load_browser_item", {
            "track_index": track_index,
            "item_uri": kit_uri
        })
        
        return f"Loaded drum rack and kit '{loadable_kits[0].get('name')}' on track {track_index}"
    except Exception as e:
        logger.error(f"Error loading drum kit: {str(e)}")
        return f"Error loading drum kit: {str(e)}"

@mcp.tool()
def delete_device(ctx: Context, track_index: int, device_index: int) -> str:
    """
    Delete a device from a track.

    Parameters:
    - track_index: The index of the track (use -1 for master, -2/-3 for returns)
    - device_index: The index of the device to delete
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("delete_device", {
            "track_index": track_index,
            "device_index": device_index
        })
        return f"Deleted device '{result.get('deleted_device', '')}' ({result.get('device_count', '?')} devices remaining)"
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        return f"Error deleting device: {str(e)}"

@mcp.tool()
def set_device_enabled(ctx: Context, track_index: int, device_index: int, enabled: bool) -> str:
    """Enable or bypass a device (track_index -1 = master, -2/-3 = returns). Use it to A/B an effect."""
    try:
        result = get_ableton_connection().send_command("set_device_enabled", {
            "track_index": track_index, "device_index": device_index, "enabled": enabled})
        return f"{'Enabled' if enabled else 'Bypassed'} {result.get('device_name', 'device')}"
    except Exception as e:
        logger.error(f"Error setting device enabled: {str(e)}")
        return f"Error setting device enabled: {str(e)}"

@mcp.tool()
def get_drum_pads(ctx: Context, track_index: int, device_index: int = 0) -> str:
    """List the filled pads of a Drum Rack: MIDI note, pad name, device. Read this before programming a kit."""
    try:
        result = get_ableton_connection().send_command("get_drum_pads", {"track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting drum pads: {str(e)}")
        return f"Error getting drum pads: {str(e)}"

@mcp.tool()
def load_drum_pad_sample(
    ctx: Context,
    track_index: int,
    device_index: int,
    note: int,
    file_path: str,
    name: str = None,
) -> str:
    """Load one sample onto an empty Drum Rack pad (Live 12.4+).

    The command creates a DrumChain mapped to `note`, inserts Simpler, and
    loads `file_path`. Existing pad contents are never replaced.
    """
    try:
        params = {
            "track_index": track_index,
            "device_index": device_index,
            "note": note,
            "file_path": file_path,
        }
        if name is not None:
            params["name"] = name
        result = get_ableton_connection().send_command("load_drum_pad_sample", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error loading Drum Rack pad sample: {str(e)}")
        return f"Error loading Drum Rack pad sample: {str(e)}"

@mcp.tool()
def get_simpler_sample(ctx: Context, track_index: int, device_index: int) -> str:
    """Read a SimplerDevice's sample path and marker positions in integer sample frames.

    Requires a Simpler device and a Remote Script backend exposing its Sample properties.
    """
    try:
        result = get_ableton_connection().send_command("get_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting Simpler sample: {str(e)}")
        return f"Error getting Simpler sample: {str(e)}"

@mcp.tool()
def set_simpler_sample_window(
    ctx: Context,
    track_index: int,
    device_index: int,
    start_marker: Optional[int] = None,
    end_marker: Optional[int] = None,
) -> str:
    """Set optional Simpler sample start/end markers, expressed as integer sample frames.

    Requires a SimplerDevice and backend support for Sample.start_marker/end_marker;
    omitted markers remain unchanged.
    """
    try:
        params = {
            "track_index": track_index,
            "device_index": device_index,
        }
        if start_marker is not None:
            params["start_marker"] = start_marker
        if end_marker is not None:
            params["end_marker"] = end_marker
        result = get_ableton_connection().send_command("set_simpler_sample_window", params)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error setting Simpler sample window: {str(e)}")
        return f"Error setting Simpler sample window: {str(e)}"

@mcp.tool()
def replace_simpler_sample(ctx: Context, track_index: int, device_index: int, file_path: str) -> str:
    """Replace a Simpler sample from an absolute file path.

    Uses SimplerDevice.replace_sample and requires Live 12.4+; pre-12.4 builds
    must return a clear backend error. The path is passed unchanged to Live.
    """
    try:
        result = get_ableton_connection().send_command("replace_simpler_sample", {
            "track_index": track_index,
            "device_index": device_index,
            "file_path": file_path,
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error replacing Simpler sample: {str(e)}")
        return f"Error replacing Simpler sample: {str(e)}"

@mcp.tool()
def move_device(ctx: Context, track_index: int, device_index: int, target_index: int) -> str:
    """Reorder a device on a track (0 = leftmost).

    Use this to reorder MIDI effects among themselves, or audio effects.
    load_instrument_or_effect already inserts MIDI FX before the instrument.
    Live cannot place an instrument before MIDI effects (Couldn't move device).
    """
    try:
        result = get_ableton_connection().send_command("move_device", {
            "track_index": track_index, "device_index": device_index, "target_index": target_index})
        return f"Moved device {device_index} to {result.get('target_index', target_index)} on track {track_index}"
    except Exception as e:
        logger.error(f"Error moving device: {str(e)}")
        return f"Error moving device: {str(e)}"

@mcp.tool()
def get_device_sidechain(ctx: Context, track_index: int, device_index: int) -> str:
    """Read external sidechain routing on a CompressorDevice (Compressor, Glue Compressor).

    Returns available routing types/channels and the current source. Other device classes
    have no sidechain API. track_index -1 = master, -2/-3 = returns.
    """
    try:
        result = get_ableton_connection().send_command("get_device_sidechain", {
            "track_index": track_index, "device_index": device_index})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting device sidechain: {str(e)}")
        return f"Error getting device sidechain: {str(e)}"

@mcp.tool()
def set_device_sidechain(ctx: Context, track_index: int, device_index: int, routing_type_name: str, channel_name: str = None) -> str:
    """Set the external sidechain source on a CompressorDevice (Compressor, Glue Compressor).

    Use get_device_sidechain first for available routing_type_name / channel_name values
    (e.g. a kick track). Other device classes have no sidechain API.
    """
    try:
        params = {"track_index": track_index, "device_index": device_index,
                  "routing_type_name": routing_type_name}
        if channel_name is not None:
            params["channel_name"] = channel_name
        result = get_ableton_connection().send_command("set_device_sidechain", params)
        return f"Sidechain '{routing_type_name}' / {result.get('channel_name', channel_name)}"
    except Exception as e:
        logger.error(f"Error setting device sidechain: {str(e)}")
        return f"Error setting device sidechain: {str(e)}"
