# tools/

Helper scripts that compose with the Ableton MCP server but run as their own
processes. The MidigenAI bridge also supplies the shared implementation used
by the `generate_midi_continuation` MCP tool.

## midigenai_bridge.py — AI MIDI continuation

CLI that turns Ableton clip notes into an AI-generated continuation. Wraps
the [`midigenai`](https://github.com/nicholasbien/midigenai) package
(a custom transformer with MIDI-event tokenization). The model
is auto-downloaded from
[huggingface.co/nicholasbien/midigenai](https://huggingface.co/nicholasbien/midigenai)
on first use and cached at `~/.cache/huggingface/`.

### Setup

```bash
pip install "ableton-mcp-pro[ai]"
```

That installs `midigenai`, `torch`, `miditok`, `symusic`, and
`huggingface_hub`. No separate repo clone, no extra venv.

### What it does

```
JSON notes (stdin)
    ↓
build a temporary .mid file
    ↓
encode with the checkpoint's MidiTok tokenizer
    ↓
sample N tokens from the transformer (downloaded from HF on first call)
    ↓
decode back to MIDI, drop everything ≤ prompt_end_beat
    ↓
JSON notes (stdout)
```

### Usage

```bash
echo '{
  "notes": [
    {"pitch": 74, "start_time": 0,  "duration": 1, "velocity": 95},
    {"pitch": 78, "start_time": 1,  "duration": 1, "velocity": 95},
    {"pitch": 81, "start_time": 2,  "duration": 2, "velocity": 100}
  ],
  "tempo_bpm": 80,
  "max_new_tokens": 256,
  "temperature": 1.2,
  "top_k": 50,
  "prompt_end_beat": 4.0,
  "pitch_range": [60, 92]
}' | python tools/midigenai_bridge.py
```

Returns:

```json
{
  "prompt_tokens": 33,
  "generated_tokens": 256,
  "tempo_bpm": 80,
  "notes": [{"pitch": 78, "start_time": 0.0, "duration": 0.5, "velocity": 95, "mute": false}, ...]
}
```

Note start times are returned **relative to `prompt_end_beat`** so the result
drops cleanly into a fresh clip starting at beat 0.

### Knobs

| key | meaning |
|---|---|
| `notes` | seed notes — Ableton MCP format (`pitch`/`start_time`/`duration`/`velocity`) |
| `tempo_bpm` | tempo of seed *and* output (the model is tempo-agnostic; this is just decoding) |
| `max_new_tokens` | how much continuation to sample. ~4 tokens/note → 256 ≈ 60 notes |
| `temperature` | 0.5–1.5. Lower sticks closer to the prompt; higher diverges more |
| `top_k` | nucleus sampling K |
| `prompt_end_beat` | drop output notes that start before this beat (= filter out the prompt itself) |
| `pitch_range` | optional `[min, max]` MIDI pitch filter — useful when you only want, say, the lead range |
| `device` | `auto` (upstream selection), `cpu`, or `directml`. Defaults to `MIDIGENAI_DEVICE`, then `auto`. |
| `version` | which subfolder of the HF repo to load. Defaults to `MIDIGENAI_VERSION`, then the installed package's default (`v4` in the pinned DirectML setup). |
| `repo_id` | HF model repo. Defaults to `MIDIGENAI_REPO_ID` env var, then `nicholasbien/midigenai`. |

### Switching to a new model release

Three ways to point the bridge at a different version, in increasing scope:

```bash
# 1) Per-call (just for one generation):
echo '{ "notes": [...], "version": "v2" }' | python tools/midigenai_bridge.py

# 2) Per shell session:
export MIDIGENAI_VERSION=v2
python tools/midigenai_bridge.py < cfg.json

# 3) Permanent: bump DEFAULT_VERSION in midigenai/hub.py
```

To see what's published:

```python
from midigenai import list_hub_versions
list_hub_versions()         # ['v2-100m', 'v2-pilot']  # 100M is the current default
```

Adding a new version on the model author side = upload `ckpt_final.pt` and
`tokenizer.json` to a new subfolder of the HF model repo. No code changes
needed in midigenai or the bridge — both auto-discover.

### Wiring it into the Ableton workflow

The MCP workflow is:

1. `mcp__AbletonMCP__get_clip_notes` → pull a clip's notes as the seed
2. Call `generate_midi_continuation` with those notes, tempo, and knobs
3. (optional) post-filter: snap to scale, clip durations, drop anything outside the song length
4. `mcp__AbletonMCP__create_clip` + `mcp__AbletonMCP__add_notes_to_clip` on a target track to drop the result

The `[ai]` extra is optional. The MCP server can start without it, and the
tool reports a clear install hint if called without the dependencies. The
standalone CLI below remains supported and uses the same JSON note-in/note-out
contract. MCP generation defaults to a killable 90-second child-process timeout;
set `timeout_seconds` higher when first-time model download or slower hardware
needs more time.

### Prompt design

v2 was trained on single-track polyphonic MIDI (heavy on piano via Lakh +
MAESTRO + POP909 + GiantMIDI). Best results come from:

- A monophonic or lightly-polyphonic **melodic seed** (4–8 bars, ~10–15 notes)
- Single instrument (omit `program` from notes, or all on the same program)
- Avoid feeding several stacked tracks (pad chords + bass + lead) — the model
  is happiest continuing a coherent musical phrase, not multi-part arrangements

### Performance

Timing depends on the checkpoint, prompt, PyTorch build, hardware, and whether
the files are cached. Each MCP request launches a new child process, so it pays
the import/model-loading cost again. Only repeated calls inside the *same*
Python process reuse the loaded generator; the on-disk Hugging Face cache
avoids downloading the model again but is not a persistent in-memory model.

### DirectML GPU worker (Windows)

DirectML wheels do not support the main environment's Python 3.14. Keep that
environment intact and create a separate Python 3.12 worker:

```powershell
uv venv --python 3.12 .venv-directml
uv pip install --python .venv-directml/Scripts/python.exe -r tools/requirements-directml.txt
```

The requirements pin Microsoft's DirectML package, its compatible PyTorch, and
the same MidigenAI revision used for the GPU test. They do not change the MCP
host's Python or PyTorch. Use `device="directml"` with the
`generate_midi_continuation` MCP tool; it automatically selects
`.venv-directml/Scripts/python.exe`. An existing MCP server must be reloaded to
expose the new tool argument; Live and its Remote Script do **not** need a restart.
Use `MIDIGENAI_PYTHON` for a different worker executable, and optionally
`MIDIGENAI_DEVICE=directml` in the MCP server environment to make GPU execution
the default. Explicit per-call `device` takes precedence over the device env var.

The CLI uses the same bridge and JSON format:

```powershell
$cfg = @{notes=@(@{pitch=66; start_time=0; duration=1; velocity=95}); version='v4'; device='directml'; max_new_tokens=64}
$cfg | ConvertTo-Json -Depth 5 -Compress | .\.venv-directml\Scripts\python.exe tools/midigenai_bridge.py
```

Responses include `execution.device`, `execution.dtype`, and the GPU's
`execution.device_name` when using DirectML. `privateuseone:0` is PyTorch's
DirectML device label, not a CPU fallback. Generation was verified on a Radeon
RX 5700 XT with the cached `v4` checkpoint. GPU execution is opt-in: batch-one
autoregressive generation has substantial per-token overhead and is not
guaranteed to be faster than the current CPU build. No third-party model code
or attention/sampling operators were patched for this test.

## setup_jam_set.py — the Live side of a fluidclaude jam

Builds `you` (keyboard in, no instrument, MIDI To IAC Bus 3), `you (sound)`, `reply` (IAC Bus 2 /
Ch. 5) and, with `--loops bass:2,drums:10`, one track per fluidclaude loop channel; prints the
fluidclaude commands. Add an audio track "sc in" (Ext. In 1/2, Monitor In) yourself when the sc
engine plays into Live through BlackHole. Never leave `you` on All Ins: that includes the bus
fluidclaude plays on and every loop becomes a "call".

## deploy_remote_script.py / launch_ableton.py — install and open Live

```bash
python tools/deploy_remote_script.py
python tools/launch_ableton.py
```

`deploy_remote_script.py` copies every `.py` file under the selected `AbletonMCP_Remote_Script/__init__.py`, preserving nested package paths, into each discovered Live MIDI Remote Scripts `AbletonMCP` folder (ProgramData Live 12/11 on Windows, `/Applications/Ableton Live *.app` on macOS, plus User Library `Remote Scripts/AbletonMCP` when that folder exists). Non-Python files and bytecode are excluded; each copied file is verified byte-for-byte and its destination `__pycache__` is removed. Use `--source PATH_TO_PACKAGE/__init__.py` for a custom package root and repeat `--dest PATH_TO_PACKAGE/__init__.py` for explicit destinations.

`launch_ableton.py` starts Ableton Live only if a Live DAW process is not already running (it ignores Ableton Index / AbletonAudioCpl). After a Remote Script deploy, the still-running Live process keeps the old script. Use `python tools/launch_ableton.py --reload --set "C:/sets/Track.als"` to request normal shutdown, relaunch with that exact saved Set, and wait until `get_session_info.file_path` matches it (not merely the startup template or an open TCP port). The Set and executable paths are checked before shutdown. Windows shutdown targets Live's own windows by process ID and never falls back to a force-kill; an unresolved dialog returns an error instead.

Save before reload when edits need to survive. `CF_Do_not_Save 1.3` automatically chooses **Don't Save** and therefore discards unsaved edits; it is appropriate only when that is intentional, such as MCP iteration on an explicitly saved test baseline. It does not save the Set or handle every possible startup dialog. `--no-wait` launches without verifying Set readiness.

Env overrides: `ABLETON_LIVE_ROOT`, `ABLETON_MIDI_REMOTE_SCRIPTS`, `ABLETON_LIVE_EXE`, `ABLETON_USER_LIBRARY`.

## live_client.py — talk to the Remote Script from a script

`live(cmd, params)` sends one command over the port-9877 socket and returns its result, plus
`tracks()`, `track_by_name(name)`, `clear_arrangement_clips(track)` and `set_param(track, device,
name, value)`. The same protocol the MCP server speaks, for scripts and tests that don't want an
MCP round trip (the resample and clip-tool tests were written against it). Every call costs
0.4–1.5 s; keep it out of anything time-critical.
