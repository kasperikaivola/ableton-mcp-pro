"""Locate Ableton Live installs, deploy the full Remote Script package, and detect Live."""

from __future__ import annotations

import csv
import io
import json
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

SCRIPT_NAME = "AbletonMCP"
SOURCE_RELATIVE = Path("AbletonMCP_Remote_Script") / "__init__.py"
DEFAULT_PORT = 9877


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def remote_script_source(root: Path | None = None) -> Path:
    return (root or repo_root()) / SOURCE_RELATIVE


def _env_path(env: dict, key: str) -> Path | None:
    value = env.get(key)
    if not value:
        return None
    return Path(value)


def live_app_roots(*, system: str | None = None, env: dict | None = None) -> list[Path]:
    """Installed Live application roots (Live 12 Suite, Live 11, ...)."""
    env = os.environ if env is None else env
    system = system or platform.system()
    found: list[Path] = []
    override = _env_path(env, "ABLETON_LIVE_ROOT")
    if override is not None:
        found.append(override)

    if system == "Windows":
        programdata = Path(env.get("PROGRAMDATA", r"C:\ProgramData"))
        ableton = programdata / "Ableton"
        if ableton.is_dir():
            children = [p for p in ableton.iterdir() if p.is_dir() and p.name.startswith("Live")]
            children.sort(key=lambda p: p.name, reverse=True)
            found.extend(children)
        program_files = Path(env.get("PROGRAMFILES", r"C:\Program Files"))
        pf_ableton = program_files / "Ableton"
        if pf_ableton.is_dir():
            children = [p for p in pf_ableton.iterdir() if p.is_dir() and "Live" in p.name]
            children.sort(key=lambda p: p.name, reverse=True)
            found.extend(children)
    elif system == "Darwin":
        apps = Path("/Applications")
        if apps.is_dir():
            children = sorted(apps.glob("Ableton Live *.app"), key=lambda p: p.name, reverse=True)
            found.extend(children)

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        resolved = path
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def midi_remote_scripts_dir(live_root: Path, *, system: str | None = None) -> Path:
    system = system or platform.system()
    if system == "Darwin" or str(live_root).endswith(".app"):
        return live_root / "Contents" / "App-Resources" / "MIDI Remote Scripts"
    return live_root / "Resources" / "MIDI Remote Scripts"


def remote_script_dest(live_root: Path, *, system: str | None = None) -> Path:
    return midi_remote_scripts_dir(live_root, system=system) / SCRIPT_NAME / "__init__.py"


def user_library_remote_script_dest(*, system: str | None = None, home: Path | None = None, env: dict | None = None) -> Path | None:
    env = os.environ if env is None else env
    override = env.get("ABLETON_USER_LIBRARY")
    system = system or platform.system()
    home = Path.home() if home is None else Path(home)
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    elif system == "Windows":
        candidates.extend([
            home / "Documents" / "Ableton" / "User Library",
            home / "OneDrive" / "Documents" / "Ableton" / "User Library",
        ])
    else:
        candidates.append(home / "Music" / "Ableton" / "User Library")
    for library in candidates:
        dest_dir = library / "Remote Scripts" / SCRIPT_NAME
        if dest_dir.is_dir() or (library / "Remote Scripts").is_dir() or library.is_dir():
            if dest_dir.is_dir() or (library / "Remote Scripts").is_dir():
                return dest_dir / "__init__.py"
    return None


def default_destinations(*, system: str | None = None, env: dict | None = None, home: Path | None = None) -> list[Path]:
    env = os.environ if env is None else env
    dests: list[Path] = []
    extra = _env_path(env, "ABLETON_MIDI_REMOTE_SCRIPTS")
    if extra is not None:
        dests.append(extra / "__init__.py" if extra.name != "__init__.py" else extra)

    for root in live_app_roots(system=system, env=env):
        scripts = midi_remote_scripts_dir(root, system=system)
        if scripts.is_dir() or root.is_dir():
            dests.append(scripts / SCRIPT_NAME / "__init__.py")

    user_dest = user_library_remote_script_dest(system=system, home=home, env=env)
    if user_dest is not None:
        dests.append(user_dest)

    seen: set[Path] = set()
    unique: list[Path] = []
    for dest in dests:
        key = dest
        if key in seen:
            continue
        seen.add(key)
        unique.append(dest)
    return unique


def live_executable(live_root: Path, *, system: str | None = None) -> Path | None:
    system = system or platform.system()
    if system == "Darwin" or str(live_root).endswith(".app"):
        macos = live_root / "Contents" / "MacOS"
        if macos.is_dir():
            for child in macos.iterdir():
                if child.is_file():
                    return child
        return live_root
    program = live_root / "Program"
    if program.is_dir():
        matches = sorted(program.glob("Ableton Live *.exe"), key=lambda p: p.name, reverse=True)
        if matches:
            return matches[0]
    return None


def default_live_executable(*, system: str | None = None, env: dict | None = None) -> Path | None:
    env = os.environ if env is None else env
    override = _env_path(env, "ABLETON_LIVE_EXE")
    if override is not None:
        return override
    for root in live_app_roots(system=system, env=env):
        exe = live_executable(root, system=system)
        if exe is not None and (exe.exists() or str(root).endswith(".app")):
            return exe
    return None


def is_live_process_name(name: str) -> bool:
    """True for the Live DAW process, not Index / control-panel helpers."""
    stem = Path(name).stem
    lowered = stem.lower()
    if not lowered.startswith("ableton live"):
        return False
    if "index" in lowered or "audiocpl" in lowered:
        return False
    return True


def running_live_processes(*, system: str | None = None) -> list[dict]:
    system = system or platform.system()
    processes: list[dict] = []
    if system == "Windows":
        try:
            raw = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.CalledProcessError):
            return []
        for parts in csv.reader(io.StringIO(raw)):
            if len(parts) < 2:
                continue
            name, pid = parts[0], parts[1]
            if is_live_process_name(name):
                processes.append({"name": name, "pid": pid})
        return processes

    try:
        raw = subprocess.check_output(["ps", "-axo", "pid=,comm="], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        pid, _, comm = line.partition(" ")
        comm = comm.strip()
        if is_live_process_name(Path(comm).name) or is_live_process_name(comm):
            processes.append({"name": comm, "pid": pid.strip()})
    return processes


def live_is_running(*, system: str | None = None) -> bool:
    return bool(running_live_processes(system=system))


def port_is_open(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_is_open(host, port):
            return True
        time.sleep(0.4)
    return False


def wait_until_port_closed(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not port_is_open(host, port, timeout=0.3):
            return True
        time.sleep(0.3)
    return False


def ping_remote_script(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 4.0):
    """Send get_session_info. Returns the result dict, or None if Live is not answering."""
    payload = json.dumps({"type": "get_session_info", "params": {}}).encode("utf-8")
    sk = socket.socket()
    sk.settimeout(timeout)
    try:
        sk.connect((host, port))
        sk.sendall(payload)
        buf = b""
        while True:
            chunk = sk.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                data = json.loads(buf.decode("utf-8"))
                break
            except (ValueError, UnicodeDecodeError):
                continue
        else:
            return None
        if not isinstance(data, dict) or data.get("status") == "error":
            return None
        return data.get("result", data)
    except (OSError, ValueError, socket.timeout):
        return None
    finally:
        try:
            sk.close()
        except OSError:
            pass


def wait_for_remote_script(host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 180.0,
                           set_file: Path | None = None):
    """Wait for a session response and, optionally, the explicitly requested Set."""
    expected = os.path.normcase(str(Path(set_file).resolve())) if set_file else None
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = ping_remote_script(host=host, port=port, timeout=3.0)
        current = result.get("file_path") if isinstance(result, dict) else None
        if result is not None and (expected is None or (
            current and os.path.normcase(str(Path(current).resolve())) == expected
        )):
            return result
        time.sleep(0.8)
    return None


def wait_for_new_live_process(old_pids, *, system: str | None = None, timeout: float = 60.0) -> list[dict]:
    old = {str(p) for p in old_pids}
    deadline = time.time() + timeout
    while time.time() < deadline:
        procs = running_live_processes(system=system)
        fresh = [p for p in procs if str(p.get("pid")) not in old]
        if fresh:
            return fresh
        time.sleep(0.4)
    return []


def _clear_pycache(dest_py: Path) -> None:
    cache = dest_py.parent / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache)


def deploy_file(source: Path, dest: Path) -> dict:
    """Copy one Python file, verify its bytes, clear its destination cache, and return stats."""
    source = Path(source)
    dest = Path(dest)
    if not source.is_file():
        raise FileNotFoundError("Remote Script source not found: {0}".format(source))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    shutil.copy2(source, dest)
    _clear_pycache(dest)
    src_bytes = source.read_bytes()
    dst_bytes = dest.read_bytes()
    if src_bytes != dst_bytes:
        raise IOError("Deploy copy mismatch: {0}".format(dest))
    return {
        "dest": str(dest),
        "bytes": len(dst_bytes),
        "lines": dst_bytes.count(b"\n") + (0 if dst_bytes.endswith(b"\n") else 1),
    }


def deploy(source: Path | None = None, destinations: list[Path] | None = None, *, system: str | None = None, env: dict | None = None) -> list[dict]:
    """Deploy every Python file under the selected ``__init__.py`` package root.

    Relative package paths are preserved below each destination ``__init__.py``.
    Only ``.py`` files are copied; caches, bytecode, and other source files are
    ignored. Each copied file is verified byte-for-byte by ``deploy_file``.
    """
    source = Path(source) if source is not None else remote_script_source()
    if not source.is_file():
        raise FileNotFoundError("Remote Script source not found: {0}".format(source))
    dests = destinations if destinations is not None else default_destinations(system=system, env=env)
    if not dests:
        raise FileNotFoundError(
            "No Ableton MIDI Remote Scripts folder found. Set ABLETON_LIVE_ROOT or "
            "ABLETON_MIDI_REMOTE_SCRIPTS, or install Live."
        )
    package_root = source.parent
    package_files = sorted(
        (
            path
            for path in package_root.rglob("*.py")
            if path.is_file() and "__pycache__" not in path.parts
        ),
        key=lambda path: path.relative_to(package_root).as_posix(),
    )
    copied: list[dict] = []
    for dest in dests:
        destination_root = Path(dest).parent
        for package_file in package_files:
            relative = package_file.relative_to(package_root)
            copied.append(deploy_file(package_file, destination_root / relative))
    return copied


def _post_close_to_live_windows(pids=None) -> int:
    """Ask Live windows to close (WM_CLOSE). Returns how many windows were signaled."""
    if platform.system() != "Windows":
        return 0
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    target_pids = {int(pid) for pid in pids} if pids is not None else None
    count = [0]

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if target_pids is not None:
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value not in target_pids or user32.GetWindow(hwnd, 4):
                return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""
        lowered = title.lower()
        if target_pids is not None or "ableton live" in lowered or title.startswith("Live"):
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            count[0] += 1
        return True

    user32.EnumWindows(callback, 0)
    return count[0]


def quit_live(*, system: str | None = None, timeout: float = 45.0, port: int = DEFAULT_PORT) -> None:
    """Request normal shutdown; never force-kill Live or dismiss save dialogs here."""
    system = system or platform.system()
    procs = running_live_processes(system=system)
    if not procs and not port_is_open(port=port):
        return
    if system == "Windows":
        _post_close_to_live_windows(pids=[proc["pid"] for proc in procs])
    else:
        for proc in procs:
            subprocess.run(["kill", str(proc["pid"])], capture_output=True, text=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not live_is_running(system=system) and not port_is_open(port=port, timeout=0.3):
            return
        time.sleep(0.4)
    raise RuntimeError("Ableton Live did not complete normal shutdown; check for a dialog. No force-kill attempted.")


def validate_set_file(set_file: Path) -> Path:
    path = Path(set_file).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".als":
        raise ValueError("Set must be an existing .als file: {0}".format(path))
    return path


def start_live(executable: Path | None = None, *, system: str | None = None, env: dict | None = None,
               set_file: Path | None = None) -> Path:
    system = system or platform.system()
    exe = Path(executable) if executable is not None else default_live_executable(system=system, env=env)
    if exe is None:
        raise FileNotFoundError(
            "Ableton Live executable not found. Set ABLETON_LIVE_EXE or install Live."
        )
    set_path = validate_set_file(set_file) if set_file is not None else None
    if system == "Darwin" and str(exe).endswith(".app"):
        command = ["open", "-a", str(exe)]
        if set_path is not None:
            command.append(str(set_path))
        subprocess.Popen(command, start_new_session=True)
    elif system == "Windows":
        if set_path is None:
            os.startfile(str(exe))  # type: ignore[attr-defined]
        else:
            subprocess.Popen([str(exe), str(set_path)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        command = [str(exe)] + ([str(set_path)] if set_path is not None else [])
        subprocess.Popen(command, start_new_session=True)
    return exe
