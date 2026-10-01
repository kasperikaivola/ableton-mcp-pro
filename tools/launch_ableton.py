#!/usr/bin/env python3
"""Start Ableton Live only if a Live DAW instance is not already running.

Does not match helper processes (Ableton Index, AbletonAudioCpl). After a Remote
Script deploy, pass --reload to quit Live and start it again so the new script loads.

    python tools/launch_ableton.py
    python tools/launch_ableton.py --reload
    python tools/launch_ableton.py --reload --set "C:/sets/Track.als"

Overrides: ABLETON_LIVE_EXE, ABLETON_LIVE_ROOT.
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
        description="Launch Ableton Live if it is not already open."
    )
    parser.add_argument(
        "--exe",
        type=Path,
        help="Path to the Live executable or .app. Default: discovered Live 12/11 install.",
    )
    parser.add_argument(
        "--set",
        dest="set_file",
        type=Path,
        help="Open this saved .als Set; validate it before quitting and wait for its path in session readback.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Quit a running Live instance, then launch so a newly deployed Remote Script loads.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for the Remote Script after launching.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=180.0,
        help="Seconds to wait for get_session_info after launch (default 180).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=inst.DEFAULT_PORT,
        help="Remote Script TCP port to wait for (default 9877).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print status as JSON.",
    )
    return parser.parse_args(argv)


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(payload.get("message", payload.get("status")))
    if payload.get("exe"):
        print("exe: {0}".format(payload["exe"]))
    if payload.get("set_file"):
        print("set: {0}".format(payload["set_file"]))
    if payload.get("remote_script"):
        print("Remote Script ready on port {0} (tempo {1})".format(
            payload.get("port", inst.DEFAULT_PORT),
            payload["remote_script"].get("tempo")))
    elif payload.get("port_open") is True:
        print("Port {0} is open but get_session_info did not answer yet.".format(
            payload.get("port", inst.DEFAULT_PORT)))
    elif payload.get("launched") and payload.get("port_open") is False:
        print("Live started but port {0} is not open yet (Control Surface AbletonMCP not ready?)".format(
            payload.get("port", inst.DEFAULT_PORT)))


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.set_file is not None:
        try:
            args.set_file = inst.validate_set_file(args.set_file)
        except (OSError, ValueError) as exc:
            _emit({"status": "error", "message": "Invalid Set: {0}".format(exc)}, args.json)
            return 1
    old_procs = inst.running_live_processes()
    running = bool(old_procs)
    payload = {
        "port": args.port,
        "port_open": inst.port_is_open(port=args.port),
        "already_running": running,
        "launched": False,
        "reloaded": False,
        "remote_script": None,
        "set_file": str(args.set_file) if args.set_file else None,
    }
    if running and not args.reload:
        payload["status"] = "already_running"
        payload["message"] = "Ableton Live is already running; not starting a second instance."
        payload["processes"] = old_procs
        payload["remote_script"] = inst.ping_remote_script(port=args.port, timeout=5.0)
        payload["port_open"] = payload["remote_script"] is not None or inst.port_is_open(port=args.port)
        _emit(payload, args.json)
        return 0

    executable = args.exe or inst.default_live_executable()
    if executable is None or not Path(executable).exists():
        payload.update(status="error", message="Ableton Live executable not found; no shutdown attempted.")
        _emit(payload, args.json)
        return 1

    if args.reload and running:
        try:
            inst.quit_live(port=args.port)
        except Exception as exc:
            payload["status"] = "error"
            payload["message"] = "Could not quit Ableton Live: {0}".format(exc)
            _emit(payload, args.json)
            return 1
        payload["reloaded"] = True
        running = False

    try:
        exe = inst.start_live(executable, set_file=args.set_file)
    except Exception as exc:
        payload["status"] = "error"
        payload["message"] = str(exc)
        _emit(payload, args.json)
        return 1

    payload["launched"] = True
    payload["exe"] = str(exe)
    payload["already_running"] = False
    old_pids = [p.get("pid") for p in old_procs]
    if not args.no_wait:
        fresh = inst.wait_for_new_live_process(old_pids, timeout=min(60.0, args.wait_timeout))
        payload["processes"] = fresh or inst.running_live_processes()
        session = inst.wait_for_remote_script(port=args.port, timeout=args.wait_timeout, set_file=args.set_file)
        payload["remote_script"] = session
        payload["port_open"] = session is not None or inst.port_is_open(port=args.port)
        if session is None:
            payload["status"] = "launched_not_ready"
            payload["message"] = (
                "Launched Ableton Live, but the Remote Script did not answer get_session_info "
                "on port {0}. Dismiss any Live dialog first (crash recovery, MIDI-note API warning), "
                "and confirm Preferences > Link/Tempo/MIDI has Control Surface AbletonMCP."
            ).format(args.port)
            _emit(payload, args.json)
            return 2
    else:
        payload["port_open"] = inst.port_is_open(port=args.port)
        payload["remote_script"] = inst.ping_remote_script(port=args.port, timeout=2.0)

    payload["status"] = "launched"
    payload["message"] = "Launched Ableton Live."
    _emit(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
