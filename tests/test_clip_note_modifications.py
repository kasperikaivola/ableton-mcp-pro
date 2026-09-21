import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_SCRIPT = ROOT / "AbletonMCP_Remote_Script"

remote_package = types.ModuleType("AbletonMCP_Remote_Script")
remote_package.__path__ = [str(REMOTE_SCRIPT)]
sys.modules.setdefault("AbletonMCP_Remote_Script", remote_package)

mixins_package = types.ModuleType("AbletonMCP_Remote_Script.mixins")
mixins_package.__path__ = [str(REMOTE_SCRIPT / "mixins")]
sys.modules.setdefault("AbletonMCP_Remote_Script.mixins", mixins_package)

from AbletonMCP_Remote_Script.mixins.clips_notes import ClipsNotesMixin


class _Note:
    note_id = 7
    pitch = 60
    start_time = 0.0
    duration = 1.0
    velocity = 80
    mute = False
    probability = 1.0
    velocity_deviation = 0.0
    release_velocity = 64


class _NativeMidiNoteVector(list):
    pass


class _Clip:
    length = 4.0

    def __init__(self):
        self.applied_notes = None
        self.native_notes = _NativeMidiNoteVector([_Note()])

    def get_notes_extended(self, **_kwargs):
        return self.native_notes

    def apply_note_modifications(self, notes):
        if notes is not self.native_notes:
            raise TypeError("expected the native MIDI note vector")
        self.applied_notes = notes


class _Harness(ClipsNotesMixin):
    def __init__(self, clip):
        self.clip = clip

    @staticmethod
    def _safe_getattr(value, name, default=None):
        return getattr(value, name, default)

    def _session_clip(self, *_args, **_kwargs):
        return self.clip

    @staticmethod
    def log_message(_message):
        pass


def test_apply_note_modifications_passes_note_sequence_to_python_lom():
    clip = _Clip()
    harness = _Harness(clip)

    harness._apply_note_modifications(0, 0, [{"note_id": 7, "velocity": 96}])

    assert clip.applied_notes is clip.native_notes
    assert clip.applied_notes[0].note_id == 7
    assert clip.applied_notes[0].velocity == 96
