"""MCP wrapper for the optional MidigenAI MIDI continuation bridge."""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context

from ..runtime import logger, mcp


_BRIDGE_PATH = Path(__file__).resolve().parents[2] / "tools" / "midigenai_bridge.py"
_DIRECTML_PYTHON = _BRIDGE_PATH.parents[1] / ".venv-directml" / "Scripts" / "python.exe"


def _generation_python(device: Optional[str]) -> str:
    """Keep the MCP host environment unchanged when using a GPU worker."""
    override = os.environ.get("MIDIGENAI_PYTHON")
    if override:
        python = Path(override).expanduser().resolve()
        if not python.is_file():
            raise FileNotFoundError(f"MIDIGENAI_PYTHON does not exist: {python}")
        return str(python)
    device = device or os.environ.get("MIDIGENAI_DEVICE", "auto")
    if device == "directml" and _DIRECTML_PYTHON.is_file():
        return str(_DIRECTML_PYTHON)
    return sys.executable


def _run_bridge_subprocess(payload: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
    """Run generation out of process so a stuck model can be terminated."""
    completed = subprocess.run(
        [_generation_python(payload.get("device")), str(_BRIDGE_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "generation process failed"
        raise RuntimeError(detail.splitlines()[-1])
    return json.loads(completed.stdout)


@mcp.tool()
def generate_midi_continuation(
    ctx: Context,
    notes: List[Dict[str, Any]],
    tempo_bpm: float = 120.0,
    max_new_tokens: int = 256,
    temperature: float = 1.2,
    top_k: int = 50,
    prompt_end_beat: Optional[float] = None,
    pitch_range: Optional[List[int]] = None,
    version: Optional[str] = None,
    repo_id: Optional[str] = None,
    timeout_seconds: float = 90.0,
    device: Optional[str] = None,
) -> str:
    """Generate MIDI with auto/cpu/directml, bounded by timeout_seconds.

    DirectML uses the isolated .venv-directml worker when installed, or the
    MIDIGENAI_PYTHON override. Returned execution fields confirm actual placement.
    """
    del ctx
    try:
        timeout_seconds = float(timeout_seconds)
        if timeout_seconds <= 0:
            return "Error generating MIDI continuation: timeout_seconds must be positive"
        if device is not None and device not in ("auto", "cpu", "directml"):
            return "Error generating MIDI continuation: device must be auto, cpu, or directml"
        payload = {
            "notes": notes,
            "tempo_bpm": tempo_bpm,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "prompt_end_beat": prompt_end_beat,
            "pitch_range": pitch_range,
            "version": version,
            "repo_id": repo_id,
        }
        if device is not None:
            payload["device"] = device
        result = _run_bridge_subprocess(payload, timeout_seconds)
        return json.dumps(result)
    except subprocess.TimeoutExpired:
        return f"Error generating MIDI continuation: timed out after {timeout_seconds:g} seconds"
    except Exception as exc:
        logger.error("Error generating MIDI continuation: %s", exc)
        return f"Error generating MIDI continuation: {exc}"
