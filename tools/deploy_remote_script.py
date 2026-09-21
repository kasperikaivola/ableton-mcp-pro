#!/usr/bin/env python3
"""Copy the complete AbletonMCP_Remote_Script Python package into Live.

The selected ``__init__.py`` determines the source package root. Every Python
module below that root is copied with its relative path; non-Python files and
bytecode caches are ignored. Each file is verified after copying, and the
destination cache for each copied directory is cleared. The command discovers
Live 12/11 Suite (and User Library Remote Scripts when that folder exists).

    python tools/deploy_remote_script.py

Overrides: ABLETON_LIVE_ROOT, ABLETON_MIDI_REMOTE_SCRIPTS, ABLETON_USER_LIBRARY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ableton_install as inst  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Deploy the AbletonMCP Remote Script into Live's MIDI Remote Scripts folder."
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Package __init__.py (default: repo AbletonMCP_Remote_Script/__init__.py); all nested .py files deploy",
    )
    parser.add_argument(
        "--dest",
        action="append",
        type=Path,
        help="Destination __init__.py or AbletonMCP folder. Repeatable. Default: discovered Live installs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the copied destinations as JSON.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    dests = None
    if args.dest:
        dests = []
        for dest in args.dest:
            dests.append(dest / "__init__.py" if dest.name != "__init__.py" else dest)
    try:
        copied = inst.deploy(source=args.source, destinations=dests)
    except Exception as exc:
        print("deploy failed: {0}".format(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"copied": copied}, indent=2))
    else:
        for item in copied:
            print("deployed {0} ({1} lines)".format(item["dest"], item["lines"]))
        print(
            "Remote Script changes load only after a full Ableton quit and relaunch. "
            "python tools/launch_ableton.py starts Live only if it is not already running; "
            "use python tools/launch_ableton.py --reload to quit and relaunch."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
