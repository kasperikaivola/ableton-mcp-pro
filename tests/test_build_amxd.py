"""Tests for MaxForLive/build_amxd.py install path and copy behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MAX_DIR = Path(__file__).resolve().parents[1] / "MaxForLive"
if str(MAX_DIR) not in sys.path:
    sys.path.insert(0, str(MAX_DIR))

import build_amxd  # noqa: E402


class UserLibraryPathTests(unittest.TestCase):
    def test_macos_default(self):
        home = Path("/Users/demo")
        got = build_amxd.user_library_root(system="Darwin", home=home, env={})
        self.assertEqual(got, home / "Music" / "Ableton" / "User Library")

    def test_windows_default(self):
        home = Path("C:/Users/demo")
        got = build_amxd.user_library_root(system="Windows", home=home, env={})
        self.assertEqual(got, home / "Documents" / "Ableton" / "User Library")

    def test_env_override_wins(self):
        home = Path("C:/Users/demo")
        env = {"ABLETON_USER_LIBRARY": "D:/Custom/User Library"}
        got = build_amxd.user_library_root(system="Windows", home=home, env=env)
        self.assertEqual(got, Path("D:/Custom/User Library"))

    def test_windows_uses_existing_onedrive_library(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            onedrive = home / "OneDrive" / "Documents" / "Ableton" / "User Library"
            onedrive.mkdir(parents=True)
            got = build_amxd.user_library_root(system="Windows", home=home, env={})
            self.assertEqual(got, onedrive)

    def test_device_dir_nests_under_user_library(self):
        library = Path("C:/Users/demo/Documents/Ableton/User Library")
        got = build_amxd.device_install_dir(user_library=library)
        self.assertEqual(
            got,
            library / "Presets" / "Audio Effects" / "Max Audio Effect" / "AbletonMCP",
        )


class InstallDeviceTests(unittest.TestCase):
    def _source_tree(self, root: Path) -> Path:
        src = root / "MaxForLive"
        (src / "code").mkdir(parents=True)
        (src / "AbletonMCP.amxd").write_bytes(b"amxd")
        (src / "code" / "tcp-server.js").write_text("tcp", encoding="utf-8")
        (src / "code" / "lom-handler.js").write_text("lom", encoding="utf-8")
        return src

    def test_copies_amxd_and_js_files_flat(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._source_tree(root)
            dest = root / "dest"
            copied = build_amxd.install_device(src, dest)
            names = sorted(path.name for path in copied)
            self.assertEqual(names, ["AbletonMCP.amxd", "lom-handler.js", "tcp-server.js"])
            self.assertEqual((dest / "AbletonMCP.amxd").read_bytes(), b"amxd")
            self.assertEqual((dest / "tcp-server.js").read_text(encoding="utf-8"), "tcp")
            self.assertEqual((dest / "lom-handler.js").read_text(encoding="utf-8"), "lom")
            self.assertFalse((dest / "code").exists())

    def test_removes_leftover_code_subfolder(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._source_tree(root)
            dest = root / "dest"
            leftover = dest / "code"
            leftover.mkdir(parents=True)
            (leftover / "old.js").write_text("stale", encoding="utf-8")
            build_amxd.install_device(src, dest)
            self.assertFalse(leftover.exists())
            self.assertFalse((dest / "old.js").exists())

    def test_replaces_existing_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._source_tree(root)
            dest = root / "dest"
            dest.mkdir()
            (dest / "AbletonMCP.amxd").write_bytes(b"old")
            build_amxd.install_device(src, dest)
            self.assertEqual((dest / "AbletonMCP.amxd").read_bytes(), b"amxd")

    def test_missing_amxd_raises(self):
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "MaxForLive"
            (src / "code").mkdir(parents=True)
            (src / "code" / "tcp-server.js").write_text("tcp", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                build_amxd.install_device(src, Path(tmp) / "dest")


if __name__ == "__main__":
    unittest.main()
