"""
MIDI Gen AI Bridge: Ableton MCP clip notes -> AI MIDI generation -> notes back.

Uses the [midigenai](https://github.com/nicholasbien/midigenai) package directly;
the model is downloaded from HuggingFace on first use and cached locally.

Reads JSON config from stdin:
  {
    "notes": [{"pitch": 62, "start_time": 0.0, "duration": 0.5, "velocity": 100}, ...],
    "tempo_bpm": 80.0,
    "max_new_tokens": 256, "temperature": 1.2, "top_k": 50,
    "prompt_end_beat": 32.0,           # filter output to notes after this beat
    "pitch_range": [60, 96],           # optional pitch filter
    "device": "directml",              # auto (default), cpu, or directml
    "version": "v4",                   # which subfolder of the HF repo to load
                                       # (default: $MIDIGENAI_VERSION env var, then midigenai's DEFAULT_VERSION)
    "repo_id": "nicholasbien/midigenai" # default: $MIDIGENAI_REPO_ID, then "nicholasbien/midigenai"
  }

Writes JSON to stdout:
  {"prompt_tokens": int, "generated_tokens": int, "tempo_bpm": float,
   "notes": [{"pitch", "start_time", "duration", "velocity"}, ...]}

Switching to a new model release in the future:
  1. Push the new model to a new subfolder on the HF repo
  2. Either bump `MIDIGENAI_VERSION` env var (no code change), pass
     `"version"` in the JSON payload, or update midigenai's
     `hub.py::DEFAULT_VERSION`. Whichever is most convenient.

Run with whatever Python env has the `[ai]` extras installed:
  pip install "ableton-mcp-pro[ai]"
  python tools/midigenai_bridge.py < cfg.json
"""

import json
import os
import sys
import tempfile
from pathlib import Path

TPQ = 480

# Lazy global so repeated calls in the same process don't reload the model
_GENERATOR = None


class MidigenAIDependencyError(RuntimeError):
    """Raised when the optional MidigenAI dependencies are unavailable."""


def _dependency_error(exc):
    return MidigenAIDependencyError(
        'MidigenAI requires the optional AI dependencies. '
        'Install them with `pip install "ableton-mcp-pro[ai]"`.'
    )


def _get_generator(repo_id, version, device=None):
    """Cache one generator per model and requested execution device."""
    global _GENERATOR
    device = device or os.environ.get("MIDIGENAI_DEVICE", "auto")
    if device not in ("auto", "cpu", "directml"):
        raise ValueError("device must be auto, cpu, or directml")
    cache_key = (repo_id, version, device)
    if _GENERATOR is None or _GENERATOR[0] != cache_key:
        generator_kwargs = {}
        if device == "directml":
            try:
                import torch_directml
            except ModuleNotFoundError as exc:
                raise MidigenAIDependencyError(
                    "DirectML requires torch-directml in a compatible Python environment. "
                    "See tools/README.md for the isolated GPU setup."
                ) from exc
            generator_kwargs = {"device": torch_directml.device(), "backend": "torch"}
        elif device == "cpu":
            import torch
            generator_kwargs = {"device": torch.device("cpu"), "backend": "torch"}
        from midigenai import load_from_hub
        gen = load_from_hub(version=version, repo_id=repo_id, **generator_kwargs)
        _GENERATOR = (cache_key, gen)
    return _GENERATOR[1]


def notes_to_score(notes, tempo_bpm):
    from symusic import Score, Track, Note, Tempo
    score = Score(TPQ)
    score.tempos = [Tempo(time=0, qpm=tempo_bpm)]

    by_program = {}
    for n in notes:
        prog = int(n.get("program", 0))
        by_program.setdefault(prog, []).append(n)

    for prog, ns in by_program.items():
        track = Track(program=prog, is_drum=False, name=f"prog{prog}")
        for n in ns:
            track.notes.append(Note(
                time=int(round(float(n["start_time"]) * TPQ)),
                duration=max(1, int(round(float(n["duration"]) * TPQ))),
                pitch=int(n["pitch"]),
                velocity=int(n["velocity"]),
            ))
        score.tracks.append(track)
    return score


def score_to_notes(score, prompt_end_beat=None, pitch_range=None):
    notes = []
    tpq = score.ticks_per_quarter
    for track in score.tracks:
        for n in track.notes:
            start_beat = float(n.start) / tpq
            dur_beat = float(n.duration) / tpq
            pitch = int(n.pitch)
            if prompt_end_beat is not None and start_beat < prompt_end_beat - 1e-6:
                continue
            if pitch_range is not None and not (pitch_range[0] <= pitch <= pitch_range[1]):
                continue
            notes.append({
                "pitch": pitch,
                "start_time": round(start_beat - (prompt_end_beat or 0), 4),
                "duration": round(dur_beat, 4),
                "velocity": int(n.velocity),
                "mute": False,
            })
    notes.sort(key=lambda x: (x["start_time"], x["pitch"]))
    return notes


def generate_midi_continuation(
    notes,
    tempo_bpm=120.0,
    max_new_tokens=256,
    temperature=1.2,
    top_k=50,
    prompt_end_beat=None,
    pitch_range=None,
    version=None,
    repo_id=None,
    device=None,
):
    """Generate a continuation and return the bridge's note-output payload.

    The AI packages remain imported only when this function is called. The
    generator cache is process-wide; separate MCP worker processes reload it.
    """
    tempo = float(tempo_bpm)
    max_new_tokens = int(max_new_tokens)
    temperature = float(temperature)
    top_k = int(top_k)
    if prompt_end_beat is not None:
        prompt_end_beat = float(prompt_end_beat)

    in_path = None
    out_path = None
    try:
        score = notes_to_score(notes, tempo)
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            in_path = Path(f.name)
        score.dump_midi(str(in_path))

        gen = (
            _get_generator(repo_id, version, device)
            if device is not None else _get_generator(repo_id, version)
        )
        prompt_ids = gen.encode_midi_file(str(in_path))

        out_path = in_path.with_name(f"{in_path.stem}_out.mid")
        new_ids = gen.generate_to_midi(
            prompt_ids,
            str(out_path),
            tempo_bpm=tempo,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
        )

        from symusic import Score

        out_score = Score(str(out_path))
        out_notes = score_to_notes(
            out_score,
            prompt_end_beat=prompt_end_beat,
            pitch_range=pitch_range,
        )
        result = {
            "prompt_tokens": len(prompt_ids),
            "generated_tokens": len(new_ids),
            "tempo_bpm": tempo,
            "notes": out_notes,
        }
        if hasattr(gen, "device"):
            execution = {
                "device": str(gen.device),
                "backend": getattr(gen, "backend", "torch"),
                "dtype": str(getattr(gen, "dtype", "unknown")),
            }
            if getattr(gen.device, "type", None) == "privateuseone":
                import torch_directml
                execution["device_name"] = torch_directml.device_name(gen.device.index).rstrip("\x00")
            result["execution"] = execution
        return result
    except ModuleNotFoundError as exc:
        raise _dependency_error(exc) from exc
    finally:
        for path in (in_path, out_path):
            if path is not None:
                path.unlink(missing_ok=True)


def main():
    cfg = json.loads(sys.stdin.read())
    result = generate_midi_continuation(
        notes=cfg["notes"],
        tempo_bpm=cfg.get("tempo_bpm", 120.0),
        max_new_tokens=cfg.get("max_new_tokens", 256),
        temperature=cfg.get("temperature", 1.2),
        top_k=cfg.get("top_k", 50),
        prompt_end_beat=cfg.get("prompt_end_beat"),
        pitch_range=cfg.get("pitch_range"),
        # None lets midigenai resolve env vars and its DEFAULT_VERSION.
        version=cfg.get("version"),
        repo_id=cfg.get("repo_id"),
        device=cfg.get("device"),
    )
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
