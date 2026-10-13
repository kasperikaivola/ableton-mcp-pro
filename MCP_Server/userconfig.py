"""Local path defaults for asset search and plugin preset loading."""

from __future__ import annotations

import json
import os
from pathlib import Path


PLUGIN_PATH_KEYS = (
    "preset_template",
    "host_preset_template",
    "generated_presets_path",
)
PLUGIN_KEYS = ("device_name", *PLUGIN_PATH_KEYS, "browser_path")
HISTORICAL_ASSET_LIBRARY = "G:/AudioAssets"


def config_file(explicit=None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve(strict=True)
    override = os.environ.get("ABLETON_MCP_USERCONFIG")
    if override:
        return Path(override).expanduser().resolve(strict=True)
    return Path(__file__).resolve().parents[1] / "userconfig.json"


def _absolute(base: Path, value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return str(path.resolve())


def load_user_config(explicit=None) -> dict:
    path = config_file(explicit)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("userconfig.json must be an object.")
    library = data.get("asset_library_path")
    if not isinstance(library, str) or not library.strip():
        raise ValueError("asset_library_path is required.")
    plugins = data.get("plugins")
    if not isinstance(plugins, dict) or not plugins:
        raise ValueError("plugins must be a non-empty object.")
    base = path.parent
    resolved = {
        "config_path": str(path),
        "asset_library_path": _absolute(base, library.strip()),
        "plugins": {},
    }
    for plugin_id, entry in plugins.items():
        if not isinstance(entry, dict):
            raise ValueError(f"plugins.{plugin_id} must be an object.")
        missing = [
            key for key in PLUGIN_KEYS
            if not isinstance(entry.get(key), str) or not entry[key].strip()
        ]
        if missing:
            raise ValueError(
                f"plugins.{plugin_id} missing {', '.join(missing)}."
            )
        plugin = {
            key: entry[key].strip()
            for key in PLUGIN_KEYS
        }
        for key in PLUGIN_PATH_KEYS:
            plugin[key] = _absolute(base, plugin[key])
        resolved["plugins"][plugin_id] = plugin
    return resolved


def require_plugin(config: dict, plugin_id: str) -> dict:
    plugins = config["plugins"]
    if plugin_id not in plugins:
        known = ", ".join(sorted(plugins))
        raise ValueError(
            f"Unknown plugin '{plugin_id}'. Configured plugins: {known}."
        )
    return plugins[plugin_id]


def asset_library_path() -> str:
    try:
        return load_user_config()["asset_library_path"]
    except Exception:
        return HISTORICAL_ASSET_LIBRARY
