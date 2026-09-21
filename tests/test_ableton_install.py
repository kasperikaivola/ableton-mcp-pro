"""Tests for tools/ableton_install.py path discovery, deploy copy, and Live process matching."""

from __future__ import annotations

import json
import socket
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ableton_install as inst  # noqa: E402


class ProcessNameTests(unittest.TestCase):
    def test_live_suite_matches(self):
        self.assertTrue(inst.is_live_process_name("Ableton Live 12 Suite.exe"))
        self.assertTrue(inst.is_live_process_name("Ableton Live 11 Standard"))

    def test_helpers_do_not_match(self):
        self.assertFalse(inst.is_live_process_name("Ableton Index.exe"))
        self.assertFalse(inst.is_live_process_name("AbletonAudioCpl.exe"))
        self.assertFalse(inst.is_live_process_name("chrome.exe"))


class PathDiscoveryTests(unittest.TestCase):
    def test_windows_live_12_dest(self):
        root = Path(r"C:\ProgramData\Ableton\Live 12 Suite")
        dest = inst.remote_script_dest(root, system="Windows")
        self.assertEqual(
            dest,
            root / "Resources" / "MIDI Remote Scripts" / "AbletonMCP" / "__init__.py",
        )

    def test_macos_live_12_dest(self):
        root = Path("/Applications/Ableton Live 12 Suite.app")
        dest = inst.remote_script_dest(root, system="Darwin")
        self.assertEqual(
            dest,
            root / "Contents" / "App-Resources" / "MIDI Remote Scripts" / "AbletonMCP" / "__init__.py",
        )

    def test_live_app_roots_windows_programdata(self):
        with TemporaryDirectory() as tmp:
            programdata = Path(tmp)
            suite = programdata / "Ableton" / "Live 12 Suite"
            suite.mkdir(parents=True)
            (programdata / "Ableton" / "Live 11 Suite").mkdir()
            roots = inst.live_app_roots(
                system="Windows",
                env={"PROGRAMDATA": str(programdata), "PROGRAMFILES": str(programdata / "pf")},
            )
            names = [p.name for p in roots]
            self.assertEqual(names[0], "Live 12 Suite")
            self.assertIn("Live 11 Suite", names)

    def test_env_live_root_first(self):
        with TemporaryDirectory() as tmp:
            custom = Path(tmp) / "CustomLive"
            custom.mkdir()
            roots = inst.live_app_roots(
                system="Windows",
                env={"ABLETON_LIVE_ROOT": str(custom), "PROGRAMDATA": str(Path(tmp) / "empty")},
            )
            self.assertEqual(roots[0], custom)

    def test_user_library_dest_when_remote_scripts_exist(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            rs = home / "Documents" / "Ableton" / "User Library" / "Remote Scripts" / "AbletonMCP"
            rs.mkdir(parents=True)
            dest = inst.user_library_remote_script_dest(system="Windows", home=home, env={})
            self.assertEqual(dest, rs / "__init__.py")

    def test_midi_remote_scripts_env(self):
        with TemporaryDirectory() as tmp:
            dest_dir = Path(tmp) / "AbletonMCP"
            dest_dir.mkdir()
            dests = inst.default_destinations(
                system="Windows",
                env={
                    "ABLETON_MIDI_REMOTE_SCRIPTS": str(dest_dir),
                    "PROGRAMDATA": str(Path(tmp) / "none"),
                    "PROGRAMFILES": str(Path(tmp) / "none"),
                },
                home=Path(tmp) / "home",
            )
            self.assertEqual(dests[0], dest_dir / "__init__.py")

    def test_windows_executable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "Live 12 Suite"
            program = root / "Program"
            program.mkdir(parents=True)
            exe = program / "Ableton Live 12 Suite.exe"
            exe.write_bytes(b"mz")
            self.assertEqual(inst.live_executable(root, system="Windows"), exe)


class DeployTests(unittest.TestCase):
    def test_copy_replaces_and_clears_pycache(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src" / "__init__.py"
            source.parent.mkdir()
            source.write_text("print('new')\n", encoding="utf-8")
            dest = root / "AbletonMCP" / "__init__.py"
            dest.parent.mkdir()
            dest.write_text("old", encoding="utf-8")
            cache = dest.parent / "__pycache__"
            cache.mkdir()
            (cache / "stale.pyc").write_bytes(b"pyc")
            info = inst.deploy_file(source, dest)
            self.assertEqual(dest.read_text(encoding="utf-8"), "print('new')\n")
            self.assertFalse(cache.exists())
            self.assertEqual(info["lines"], 1)

    def test_missing_source_raises(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                inst.deploy_file(Path(tmp) / "missing.py", Path(tmp) / "dest" / "__init__.py")

    def test_deploy_copies_plugin_params_sibling(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_dir = root / "AbletonMCP_Remote_Script"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text("print('script')\n", encoding="utf-8")
            (src_dir / "plugin_params.py").write_text("X = 1\n", encoding="utf-8")
            dest = root / "MIDI Remote Scripts" / "AbletonMCP" / "__init__.py"
            copied = inst.deploy(source=src_dir / "__init__.py", destinations=[dest])
            self.assertEqual(dest.read_text(encoding="utf-8"), "print('script')\n")
            self.assertEqual((dest.parent / "plugin_params.py").read_text(encoding="utf-8"), "X = 1\n")
            self.assertEqual(len(copied), 2)


class RemoteScriptPingTests(unittest.TestCase):
    def test_ping_reads_session_json(self):
        ready = threading.Event()
        port_box = []

        def serve():
            srv = socket.socket()
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_box.append(srv.getsockname()[1])
            ready.set()
            conn, _ = srv.accept()
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                try:
                    json.loads(buf.decode("utf-8"))
                    break
                except (ValueError, UnicodeDecodeError):
                    continue
            conn.sendall(json.dumps({"status": "success", "result": {"tempo": 99}}).encode("utf-8"))
            conn.close()
            srv.close()

        thread = threading.Thread(target=serve)
        thread.daemon = True
        thread.start()
        self.assertTrue(ready.wait(2.0))
        result = inst.ping_remote_script(port=port_box[0], timeout=3.0)
        thread.join(3.0)
        self.assertEqual(result.get("tempo"), 99)

    def test_ping_none_when_closed(self):
        self.assertIsNone(inst.ping_remote_script(port=1, timeout=0.3))


if __name__ == "__main__":
    unittest.main()
