from pathlib import Path
import sys


REMOTE_SCRIPT = Path(__file__).resolve().parents[1] / "AbletonMCP_Remote_Script"
sys.path.insert(0, str(REMOTE_SCRIPT))

from mixins.simpler import SimplerMixin
from mixins.transport_mixer import TransportMixerMixin


class _FakeApp:
    current_dialog_message = ""
    current_dialog_button_count = 0
    open_dialog_count = 0

    def __init__(self, minor_version=4):
        self.minor = minor_version

    def get_major_version(self):
        return 12

    def get_minor_version(self):
        return self.minor

    def get_bugfix_version(self):
        return 0

    def get_version_string(self):
        return "12.{0}.0".format(self.minor)


class _FakeSimpler:
    name = "Simpler"

    def __init__(self):
        self.file_path = None

    def replace_sample(self, file_path):
        self.file_path = file_path


class _FakeChain:
    def __init__(self):
        self.in_note = -1
        self.name = "Chain"
        self.devices = []

    def insert_device(self, name):
        assert name == "Simpler"
        self.devices.append(_FakeSimpler())


class _FakePad:
    def __init__(self, note):
        self.note = note
        self.name = "Pad"
        self.chains = []
        self.cleanup_calls = 0

    def delete_all_chains(self):
        self.cleanup_calls += 1
        self.chains[:] = []


class _FakeRack:
    can_have_drum_pads = True
    name = "Drum Rack"

    def __init__(self):
        self.chains = []
        self.drum_pads = [_FakePad(note) for note in range(128)]

    def insert_chain(self, index):
        self.chains.insert(index, _FakeChain())


class _Harness(SimplerMixin, TransportMixerMixin):
    def __init__(self, minor_version=4):
        self.rack = _FakeRack()
        self.track = type("Track", (), {"devices": [self.rack]})()
        self.app = _FakeApp(minor_version)
        self.messages = []

    def application(self):
        return self.app

    def _get_track(self, index):
        assert index == 0
        return self.track

    @staticmethod
    def _safe_getattr(obj, name, default=None):
        return getattr(obj, name, default)

    def log_message(self, message):
        self.messages.append(message)


def test_load_drum_pad_sample_builds_chain_and_loads_simpler():
    harness = _Harness()

    result = harness._load_drum_pad_sample(0, 0, 36, "C:/samples/kick.wav", "Kick")

    chain = harness.rack.chains[0]
    assert result["loaded"] is True
    assert chain.in_note == 36
    assert chain.name == "Kick"
    assert chain.devices[0].file_path == "C:/samples/kick.wav"


def test_load_drum_pad_sample_rejects_old_live_before_mutating():
    harness = _Harness(minor_version=3)

    try:
        harness._load_drum_pad_sample(0, 0, 36, "C:/samples/kick.wav")
    except Exception as exc:
        assert "Live 12.4+" in str(exc)
    else:
        raise AssertionError("Expected Live version rejection")

    assert harness.rack.chains == []


def test_application_info_uses_live_version_methods():
    result = _Harness()._get_application_info()

    assert result["major_version"] == 12
    assert result["minor_version"] == 4
    assert result["bugfix_version"] == 0
    assert result["version"] == "12.4.0"
    assert result["open_dialog_count"] == 0
