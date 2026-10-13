"""Plugin id to host-preset packer. Serum 2 is the first adapter."""

from __future__ import annotations

from pathlib import Path

from .serum2 import pack_serum2


_ADAPTERS = {"serum2": pack_serum2}


def register_adapter(plugin_id: str, pack) -> None:
    _ADAPTERS[plugin_id] = pack


def unregister_adapter(plugin_id: str) -> None:
    _ADAPTERS.pop(plugin_id, None)


def pack_plugin_preset(plugin_id: str, source: Path, template: Path) -> tuple[bytes, dict]:
    pack = _ADAPTERS.get(plugin_id)
    if pack is None:
        known = ", ".join(sorted(_ADAPTERS)) or "none"
        raise ValueError(
            f"No preset adapter for '{plugin_id}'. Available adapters: {known}."
        )
    return pack(Path(source), Path(template))
