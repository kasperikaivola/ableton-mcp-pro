#!/usr/bin/env python3
"""Build a valid .amxd file with the required binary header."""
import argparse
import json
import os
import platform
import shutil
import struct
import time
from pathlib import Path

DEVICE_TYPE_AUDIO_EFFECT = 0x61616161  # 'aaaa'

# TCP port the device listens on. 9878 by default so it can coexist with the
# Python Remote Script (9877). Point the MCP server at it with ABLETON_PORT=9878.
PORT = 9878
DEVICE_PRESET_RELATIVE = Path("Presets") / "Audio Effects" / "Max Audio Effect" / "AbletonMCP"

patcher = {
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 8,
            "minor": 6,
            "revision": 5,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [100.0, 100.0, 640.0, 480.0],
        "bglocked": 0,
        "openinpresentation": 1,
        "default_fontsize": 12.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [15.0, 15.0],
        "gridsnaponopen": 1,
        "objectsnaponopen": 1,
        "statusbarvisible": 2,
        "toolbarvisible": 1,
        "lefttoolbarpinned": 0,
        "tede": 0,
        "default_maxclass": "",
        "default_object_width": 128,
        "description": "",
        "digest": "",
        "tags": "",
        "style": "",
        "subpatcher_template": "",
        "devicewidth": 246,
        "autosave": 0,
        "boxes": [
            {
                "box": {
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [""],
                    "patching_rect": [250.0, 30.0, 120.0, 22.0],
                    "text": "loadmess script start"
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [""],
                    "patching_rect": [30.0, 30.0, 190.0, 22.0],
                    "text": "node.script tcp-server.js " + str(PORT)
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [""],
                    "patching_rect": [30.0, 70.0, 170.0, 22.0],
                    "text": "js lom-handler.js"
                }
            },
            {
                "box": {
                    "id": "obj-7",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [30.0, 120.0, 220.0, 20.0],
                    "presentation": 1,
                    "presentation_rect": [10.0, 10.0, 226.0, 20.0],
                    "text": "AbletonMCP — TCP:" + str(PORT)
                }
            },
            {
                "box": {
                    "id": "obj-10",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": ["signal"],
                    "patching_rect": [420.0, 30.0, 70.0, 22.0],
                    "text": "plugin~"
                }
            },
            {
                "box": {
                    "id": "obj-11",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [420.0, 70.0, 80.0, 22.0],
                    "text": "plugout~"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "source": ["obj-1", 0],
                    "destination": ["obj-2", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-2", 0],
                    "destination": ["obj-3", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-3", 0],
                    "destination": ["obj-2", 0]
                }
            },
            {
                "patchline": {
                    "source": ["obj-10", 0],
                    "destination": ["obj-11", 0]
                }
            }
        ],
        "project": {
            "version": 1,
            "creationdate": int(time.time()),
            "modificationdate": int(time.time()),
            "viewrect": [0.0, 0.0, 300.0, 500.0],
            "autoorganize": 1,
            "hideprojectwindow": 1,
            "showdependencies": 1,
            "autolocalize": 0,
            "contents": {
                "patchers": {},
                "code": {}
            },
            "layout": {},
            "searchpath": {
                "code": {
                    "relative": 1,
                    "auditfolder": 1,
                    "noedit": 1
                }
            },
            "detailsvisible": 0,
            "amxdtype": DEVICE_TYPE_AUDIO_EFFECT,
            "readonly": 0,
            "devpathtype": 0,
            "devpath": ".",
            "sortmode": 0,
            "viewmode": 0
        },
        "dependency_cache": [
            {"name": "tcp-server.js", "bootpath": ".", "type": "TEXT", "implicit": 1},
            {"name": "lom-handler.js", "bootpath": ".", "type": "TEXT", "implicit": 1}
        ]
    }
}

def build_amxd(output_path, device_type, patcher_dict):
    json_bytes = json.dumps(patcher_dict, indent='\t').encode('utf-8')
    # JSON data + null terminator
    ptch_size = len(json_bytes) + 1

    header = b''
    header += b'ampf'                                    # magic
    header += struct.pack('<I', 4)                       # size of device type field
    header += struct.pack('<I', device_type)             # device type
    header += b'meta'                                    # meta marker
    header += struct.pack('<I', 4)                       # meta size
    header += struct.pack('<I', 0)                       # meta content (unfrozen)
    header += b'ptch'                                    # patch marker
    header += struct.pack('<I', ptch_size)               # patch size

    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(json_bytes)
        f.write(b'\x00')

    print(f"Built {output_path} ({len(header) + len(json_bytes) + 1} bytes)")


def user_library_root(*, system=None, home=None, env=None):
    env = os.environ if env is None else env
    override = env.get("ABLETON_USER_LIBRARY")
    if override:
        return Path(override)
    system = system or platform.system()
    home = Path.home() if home is None else Path(home)
    if system == "Windows":
        candidates = [
            home / "Documents" / "Ableton" / "User Library",
            home / "OneDrive" / "Documents" / "Ableton" / "User Library",
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]
    return home / "Music" / "Ableton" / "User Library"


def device_install_dir(*, system=None, home=None, env=None, user_library=None):
    root = Path(user_library) if user_library is not None else user_library_root(
        system=system, home=home, env=env
    )
    return root / DEVICE_PRESET_RELATIVE


def install_device(source_dir, dest_dir):
    source_dir = Path(source_dir)
    dest_dir = Path(dest_dir)
    amxd = source_dir / "AbletonMCP.amxd"
    if not amxd.is_file():
        raise FileNotFoundError(f"Built device not found: {amxd}")
    js_dir = source_dir / "code"
    js_files = sorted(js_dir.glob("*.js")) if js_dir.is_dir() else []
    dest_dir.mkdir(parents=True, exist_ok=True)
    leftover = dest_dir / "code"
    if leftover.is_dir():
        shutil.rmtree(leftover)
    copied = []
    for src in [amxd, *js_files]:
        dest = dest_dir / src.name
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        shutil.copy2(src, dest)
        copied.append(dest)
    return copied


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the AbletonMCP Max for Live device."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Copy the device and JS files into the Ableton User Library.",
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        help="Copy into this folder instead of the default User Library path.",
    )
    parser.add_argument(
        "--user-library",
        type=Path,
        help="Ableton User Library root. Overrides ABLETON_USER_LIBRARY.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    output = script_dir / "AbletonMCP.amxd"
    build_amxd(str(output), DEVICE_TYPE_AUDIO_EFFECT, patcher)
    dest = (
        args.install_dir
        if args.install_dir is not None
        else device_install_dir(user_library=args.user_library)
    )
    if not args.install and args.install_dir is None:
        print(f"To install into Ableton: python {Path(__file__).name} --install")
        print(f"Destination: {dest}")
        return
    copied = install_device(script_dir, dest)
    print(f"Installed {len(copied)} files to {dest}")
    for path in copied:
        print(f"  {path.name}")


if __name__ == "__main__":
    main()

