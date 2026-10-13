"""Load a VST by publishing a new host preset and inserting it from the browser."""

import json
from typing import Optional

from mcp.server.fastmcp import Context

from ..plugin_presets.load import load_configured_preset
from ..runtime import get_ableton_connection, logger, mcp
from ..userconfig import load_user_config


ATTEMPTS = 4
PAUSE_SECONDS = 0.4


@mcp.tool()
def get_user_config(ctx: Context) -> str:
    """Read userconfig.json paths for asset search and plugin preset loading.

    plugins.<id>.preset_template is the baseline file for a new preset design.
    Convert it, edit it into a new design, and write a separate preset file.
    One or two parameter changes are not a new preset. generated_presets_path
    is where new preset files are saved. host_preset_template is the same-build
    .vstpreset used only as container structure.
    """
    try:
        return json.dumps(load_user_config(), indent=2)
    except Exception as exc:
        logger.error(f"Error reading user config: {exc}")
        return json.dumps({"error": str(exc)})


@mcp.tool()
def load_plugin_preset(
    ctx: Context,
    plugin_id: str,
    source_path: str,
    track_index: Optional[int] = None,
    track_name: Optional[str] = None,
    host_preset_template: Optional[str] = None,
) -> str:
    """Insert a VST with a preset loaded, or replace the instrument on a MIDI track.

    Packages source_path into a new .vstpreset using the plugin's same-build
    host_preset_template (or host_preset_template when passed). Writes that new
    file under the plugin's generated_presets_path and loads the browser item
    Live actually returns. Omit track_index to create a MIDI track. Pass a
    track index to replace that track's instrument; clips and the other devices
    stay, and this does not rename the track. An existing source preset or an
    existing host preset may be used. Neither input is overwritten.

    This is not set_plugin_preset, which selects a host program bank. Serum 2
    is the registered adapter. A new preset request must already be a new
    design in source_path, not a one- or two-parameter edit. Remote Script
    browser only. loaded is true only after the device list shows the plugin.
    """
    try:
        result = load_configured_preset(
            plugin_id=plugin_id,
            source_path=source_path,
            track_index=track_index,
            track_name=track_name,
            host_preset_template=host_preset_template,
            connection=get_ableton_connection(),
            attempts=ATTEMPTS,
            pause_seconds=PAUSE_SECONDS,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error(f"Error loading plugin preset: {exc}")
        return json.dumps({"loaded": False, "error": str(exc)})
