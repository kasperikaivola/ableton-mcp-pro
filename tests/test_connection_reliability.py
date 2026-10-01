import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from MCP_Server.connection import AbletonConnection


class _ConcurrentProbeSocket:
    def __init__(self):
        self.active = 0
        self.interleaved = False

    def sendall(self, _payload):
        self.active += 1
        if self.active > 1:
            self.interleaved = True

    def recv(self, _buffer_size):
        time.sleep(0.03)
        self.active -= 1
        return json.dumps({"status": "success", "result": {}}).encode("utf-8")

    def settimeout(self, _timeout):
        pass

    def close(self):
        pass


def test_send_command_serializes_a_shared_socket_transaction():
    sock = _ConcurrentProbeSocket()
    connection = AbletonConnection("localhost", 9877, sock=sock)
    threads = [
        threading.Thread(target=connection.send_command, args=("get_session_info",))
        for _ in range(2)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert all(not thread.is_alive() for thread in threads)
    assert sock.interleaved is False


def test_remote_script_dispatches_ordinary_commands_on_live_main_thread():
    source = Path("AbletonMCP_Remote_Script/control_surface.py").read_text(encoding="utf-8")

    assert "def _run_on_main_thread" in source
    assert "self._process_command(command, on_main_thread=True)" in source


def test_server_entrypoint_supports_direct_script_import():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy; runpy.run_path('MCP_Server/server.py', run_name='entrypoint_probe')",
        ],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
