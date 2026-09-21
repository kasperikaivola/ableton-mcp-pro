# Ableton MCP Pro

Full control of Ableton Live through MCP-capable agents. Create tracks, program MIDI, load instruments, mix, automate, and record arrangements — all from natural language.

### Demo Tracks

- [claude_hardgroove](https://soundcloud.com/nicholasbien/claude_hardgroove)
- [claude_song1](https://soundcloud.com/nicholasbien/claude_song1)
- [claude_downtempo](https://soundcloud.com/nicholasbien/claude_downtempo)

Forked from [uisato/ableton-mcp-extended](https://github.com/uisato/ableton-mcp-extended), inspired by [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp).

## What's New

This fork adds significant capabilities beyond the original:

- **Direct arrangement editing** — Read, place, and delete clips in arrangement view, including MIDI note insertion, without a session-view round trip.
- **Arrangement recording** — Record session clips into the arrangement with bar-accurate scene transitions, with `start_time` to append past existing material
- **Arrangement view** — Read arrangement info, clips per track (with `file_path` for audio clips), full arrangement state; control loop, overdub, song position, and back-to-arranger
- **Arrangement playback** — Dedicated `play_arrangement` command that switches to arrangement view
- **Smooth automation envelopes** — Interpolated ramps between points (not just flat steps)
- **Full mixing** — Volume, panning, sends, mute, solo, arm for all tracks including master and returns
- **Group, return, and master robustness** — consistent indexing and guarded operations across track classes
- **Scene management** — Create, delete, rename, and fire scenes for arrangement workflows
- **Track management** — Create/delete/duplicate MIDI and audio tracks
- **Clip operations** — Duplicate, delete, rename, loop control, get/set notes
- **LOM batch operations** — Patch MIDI notes in place by `note_id`, duplicate session clips into the arrangement with envelopes, and inspect application/dialog state
- **Rack and native devices** — Rack macro values and variations, plus native Live device insertion by UI name on Live 12.3+
- **Simpler sample control** — Read/set sample windows in integer sample frames; replace samples on Live 12.4+
- **Device control** — Get/set any device parameter (including configured VST knobs by name, with inferred groups for Serum-style prefixes), batch updates, delete devices
- **Browser integration** — Browse and load instruments, effects, and presets by URI
- **Transport controls** — Tempo, time signature, metronome, record mode
- **Undo/redo** support

See [NEXT_STEPS.md](NEXT_STEPS.md) for the full feature list and roadmap.

## Music Production Skills

This project supports MCP-capable agents and includes 20 production skills for genre-specific workflows — from sound design to pattern programming to mixing. Claude discovers `.claude/skills/`; Codex discovers `.agents/skills/`. Both trees must contain exact byte-for-byte mirrors, checked with `python tools/check_skill_mirrors.py`.

### Available Skills

| Category | Skills |
|----------|--------|
| **Techno** | [techno-drums](.claude/skills/techno-drums/SKILL.md) — minimal/dark techno percussion with Operator synthesis<br>[techno-bass](.claude/skills/techno-bass/SKILL.md) — 3 Operator patches (sub, distorted, acid-influenced)<br>[hardgroove-drums](.claude/skills/hardgroove-drums/SKILL.md) — driving tom-heavy patterns with layered percussion<br>[hardgroove-bass](.claude/skills/hardgroove-bass/SKILL.md) — simple driving basslines with FM and acid variations |
| **House & Garage** | [house-drums](.claude/skills/house-drums/SKILL.md) — classic 4/4 patterns with open hats and congas<br>[house-chords](.claude/skills/house-chords/SKILL.md) — stabs, deep pads, disco filtered chords<br>[ukg-drums](.claude/skills/ukg-drums/SKILL.md) — 2-step patterns with gain staging and 5 pattern templates<br>[speed-garage](.claude/skills/speed-garage/SKILL.md) — walking FM bass, rave loops, vocal chops |
| **Trance** | [trance-bass](.claude/skills/trance-bass/SKILL.md) — 3 essential types (offbeat, filled 16ths, octave jump)<br>[trance-melodies](.claude/skills/trance-melodies/SKILL.md) — melody writing with call-and-response and tension/resolution |
| **Bass Music** | [acid-bass](.claude/skills/acid-bass/SKILL.md) — 303-style squelch with accent, slide, and distortion<br>[growl-bass](.claude/skills/growl-bass/SKILL.md) — FM synthesis growl with macro control and formant filters<br>[reese-bass](.claude/skills/reese-bass/SKILL.md) — detuned saw phasing with notch filter movement |
| **Synth & Ambient** | [supersaw-chords](.claude/skills/supersaw-chords/SKILL.md) — Wavetable unison patches with mono/stereo layering<br>[ethereal-pads](.claude/skills/ethereal-pads/SKILL.md) — split-voice chord layers with drone notes and noise<br>[ambient](.claude/skills/ambient/SKILL.md) — reverb-as-sound-design with granular textures<br>[synthwave](.claude/skills/synthwave/SKILL.md) — gated reverb, arps, retro bass and leads |
| **Production** | [mixing-guide](.claude/skills/mixing-guide/SKILL.md) — systematic mixing workflow with master chain<br>[track-arrangement](.claude/skills/track-arrangement/SKILL.md) — loop-to-full-track with genre-specific notes<br>[drum-swing](.claude/skills/drum-swing/SKILL.md) — MPC swing percentages, humanization, groove theory |

### Using Skills

Skills activate automatically based on what you ask. Examples:

- *"Make me a techno beat"* → triggers techno-drums
- *"Add an acid bassline"* → triggers acid-bass
- *"Let's mix this track"* → triggers mixing-guide
- *"Make some dreamy pads"* → triggers ethereal-pads

Skills can also be combined — ask for "techno drums and bass" and Claude will use both techno-drums and techno-bass skills together.

### Creating Your Own Skills

See the [Skill Authoring Guide](SKILL_AUTHORING_GUIDE.md) for best practices on creating new skills.

## Setup

### Prerequisites

- Ableton Live 11+ (any edition)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### 1. Clone the repo

```bash
git clone https://github.com/nicholasbien/ableton-mcp-pro.git
cd ableton-mcp-pro
```

### 2. Install the Remote Script in Ableton

Copy the Remote Script into Ableton's MIDI Remote Scripts folder:

**Mac (manual full-package copy):**
```bash
SOURCE="AbletonMCP_Remote_Script"
DEST="/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP"
mkdir -p "$DEST"
(
  cd "$SOURCE"
  find . -type f -name '*.py' ! -path '*/__pycache__/*' -print0 |
    while IFS= read -r -d '' file; do
      target="$DEST/${file#./}"
      mkdir -p "$(dirname "$target")"
      rm -f "$target"
      cp "$file" "$target"
    done
)
find "$DEST" -type d -name __pycache__ -prune -exec rm -rf {} +
```

**Windows / macOS (script):**
```bash
python tools/deploy_remote_script.py
python tools/launch_ableton.py
```

`deploy_remote_script.py` copies the complete Python package, preserving nested paths and excluding non-Python files and bytecode caches, into Live's MIDI Remote Scripts folder (and User Library `Remote Scripts/AbletonMCP` when present). `launch_ableton.py` starts Live only if it is not already running. After a Remote Script change, quit Live or pass `--reload` so the new script loads.

**Windows (manual full-package copy):**
```powershell
$source = (Resolve-Path "AbletonMCP_Remote_Script").Path
$destination = "C:\ProgramData\Ableton\Live 12 Suite\Resources\MIDI Remote Scripts\AbletonMCP"
Get-ChildItem $source -Recurse -File -Filter *.py |
  Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' } |
  ForEach-Object {
    $relative = $_.FullName.Substring($source.Length).TrimStart([char[]]@('\\', '/'))
    $target = Join-Path $destination $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    Copy-Item $_.FullName $target -Force
  }
Get-ChildItem $destination -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

> Adjust the path for your Ableton version (Live 11, Live 12, Suite vs Standard, etc).

### 3. Enable in Ableton

1. Open Ableton Live
2. Go to **Preferences** > **Link, Tempo & MIDI**
3. Set a **Control Surface** slot to **AbletonMCP**
4. Leave Input and Output set to **None**

You should see "AbletonMCP: Listening for commands on port 9877" in the status bar.

#### Alternative: Max for Live device

If you have Live Suite (or the Max for Live add-on), you can skip the Remote Script install and use the drag-and-drop device instead:

```bash
python MaxForLive/build_amxd.py --install
```

This builds the `.amxd` and copies it plus the JS files (flat, not in a `code/` subfolder) into the Ableton User Library:

- **macOS:** `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/AbletonMCP`
- **Windows:** `%USERPROFILE%\Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect\AbletonMCP`

Override the User Library root with `--user-library` or `ABLETON_USER_LIBRARY`, or pass `--install-dir` for an exact destination.

Drag **AbletonMCP** from the browser (User Library > Presets > Audio Effects > Max Audio Effect) onto any track. It listens on port **9878**, so set `ABLETON_PORT=9878` in the MCP server's environment. The device supports a broad subset of the Remote Script command set. Browser tools (`get_browser_tree`, `get_browser_items_at_path`, `load_instrument_or_effect`) are Remote Script only because Max for Live's Live API does not expose the browser. Arrangement and track queries also differ slightly by backend, so validate a workflow on the backend you use. Both backends can run at the same time. See [DEVELOPMENT.md](DEVELOPMENT.md#max-for-live-device-alternative-to-remote-script).

### 4. Connect your AI assistant

Any MCP-capable agent can connect with the same MCP server command and arguments. The examples below show common clients.

#### Claude Code (CLI)

Add to your `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "AbletonMCP": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/path/to/ableton-mcp-pro",
        "python",
        "/path/to/ableton-mcp-pro/MCP_Server/server.py"
      ]
    }
  }
}
```

#### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "AbletonMCP": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--project", "/path/to/ableton-mcp-pro",
        "python",
        "/path/to/ableton-mcp-pro/MCP_Server/server.py"
      ]
    }
  }
}
```

> Replace `/path/to/ableton-mcp-pro` with the actual path where you cloned the repo. If you don't have `uv`, you can use `pip install -e .` and replace the command with `python` and args with just the server path.

#### Cursor

Add an MCP server in **Settings > MCP** with the same command and args as above.

### 5. Try it

Open your AI assistant and try:
- "What tracks do I have?"
- "Create a MIDI track, load Analog on it, and program a bass line"
- "Set the tempo to 128 and add a compressor to the master"

## How It Works

```
AI Assistant --> MCP Server (Python) --> TCP socket (port 9877) --> Remote Script (inside Ableton)
```

1. You give a natural language instruction to your AI assistant
2. The assistant calls MCP tools like `create_clip`, `add_notes_to_clip`, `set_device_parameter`
3. The MCP server sends JSON commands over TCP to the Remote Script running inside Ableton
4. The Remote Script executes commands using Ableton's Live Object Model (LOM)

## Available Tools

### Read
`get_session_info`, `get_application_info`, `get_track_info`, `get_device_parameters`, `get_arrangement_info`, `get_arrangement_clips`, `get_full_arrangement`, `get_clip_notes`, `get_arrangement_clip_notes`, `get_clip_envelope`, `get_simpler_sample`, `get_browser_tree`, `get_browser_items_at_path`, `get_drum_pads`, `get_clip_info`, `get_groove_pool`, `get_device_sidechain`, `get_rack_chains`, `get_rack_macros`, `get_cue_points`, `get_warp_markers`, `convert_clip_time`

### Modify
`create_midi_track`, `create_audio_track`, `create_clip`, `create_arrangement_audio_clips_batch`, `resample_master`, `add_notes_to_clip`, `apply_note_modifications`, `duplicate_clip_to_arrangement`, `capture_midi`, `capture_and_insert_scene`, `set_clip_name`, `set_clip_loop`, `crop_clip`, `set_clip_launch`, `set_clip_color`, `set_clip_muted`, `set_clip_markers`, `set_clip_signature`, `set_clip_ram_mode`, `quantize_pitch`, `delete_clip`, `delete_arrangement_clip`, `duplicate_clip`, `delete_track`, `duplicate_track`, `move_device`, `set_track_name`, `set_track_volume`, `set_track_panning`, `set_track_color`, `set_track_mute`, `set_track_solo`, `set_track_arm`, `set_send_level`, `set_crossfader`, `set_crossfade_assign`, `set_tempo`, `set_time_signature`, `set_metronome`, `tap_tempo`, `jump_by`, `continue_playing`, `set_session_record`, `set_session_automation_record`, `re_enable_automation`, `set_count_in_duration`, `set_exclusive_arm`, `set_punch`, `set_song_scale`, `fire_clip`, `stop_clip`, `fire_scene`, `create_scene`, `delete_scene`, `duplicate_scene`, `set_scene_name`, `set_scene_color`, `set_scene_tempo`, `set_scene_signature`, `start_playback`, `stop_playback`, `play_arrangement`, `load_instrument_or_effect`, `insert_device`, `set_device_parameter`, `batch_set_device_parameters`, `set_plugin_preset`, `delete_device`, `set_device_sidechain`, `insert_rack_chain`, `set_chain_mixer`, `add_macro`, `remove_macro`, `randomize_macros`, `store_macro_variation`, `recall_macro_variation`, `delete_macro_variation`, `set_simpler_sample_window`, `replace_simpler_sample`, `press_current_dialog_button`, `apply_groove`, `clear_clip_groove`, `set_groove_amount`, `toggle_cue`, `jump_to_cue`, `set_cue_volume`, `show_view`, `add_warp_marker`, `move_warp_marker`, `delete_warp_marker`, `set_song_time`, `set_record_mode`, `set_arrangement_overdub`, `set_back_to_arranger`, `set_arrangement_loop`, `set_clip_envelope`, `clear_clip_envelope`, `undo`, `redo`, `remove_notes`, `quantize_clip`, `duplicate_clip_loop`, `duplicate_region`, `set_device_enabled`, `create_return_track`, `delete_return_track`, `stop_all_clips`, `set_clip_gain`, `set_clip_pitch`, `set_clip_warping`, `set_clip_warp_mode`

### Arrangement
The arrangement view supports a **full read-modify-write loop directly**, no session-view round-trip required:

- `get_arrangement_clips(track_index)` — list clips on a track with `start_time`, `length`, and (for audio) `file_path` of the source sample.
- `get_arrangement_clip_notes(track_index, arrangement_clip_index)` — read MIDI notes from any arrangement clip.
- `create_arrangement_audio_clip(track_index, file_path, time, length?)` — place a sample directly at a beat position. Pair with `file_path` from `get_arrangement_clips` to clone/remix existing samples.
- `create_arrangement_midi_clip(track_index, time, length, notes?)` — create a MIDI clip and (optionally) seed all notes inline in one call.
- `delete_arrangement_clip(track_index, arrangement_clip_index)` — remove a clip by index.
- `record_arrangement(sections, start_time?)` — record session scenes into arrangement with bar-accurate transitions; `start_time` appends past existing material instead of overwriting from beat 0.

#### Session vs. arrangement workflow

Both views are useful — pick based on what you're doing:

- **Use session view** for iteration: building a chord progression, dialing in a drum pattern, A/B-ing variations, or anywhere the agent benefits from tight `create_clip` → `add_notes_to_clip` → `fire_clip` loops where the user can hear changes immediately.
- **Use arrangement view** for the final song structure: build, drops, breaks, transitions. Once a section is right, the agent should prefer `create_arrangement_midi_clip` / `create_arrangement_audio_clip` to place the section directly in arrangement at the target beat position rather than re-recording session clips. This keeps the timeline clean (no overdubbed takes), avoids overwriting existing arrangement material, and lets the agent edit the final song surgically — read what's there with `get_arrangement_clips` / `get_arrangement_clip_notes`, swap or delete with `delete_arrangement_clip`, and place new material at exact beat positions.

`duplicate_clip_to_arrangement` is the direct session-to-arrangement copy operation. It copies the selected session clip, including its envelopes, to `destination_time` on the same track.

### LOM batch boundaries

- Rack commands add/remove/randomize macros and store/recall/delete variations. `get_rack_macros` reports `visible_macro_count`, `variation_count`, `selected_variation_index`, and mapped macros; new macro mappings remain GUI-only.
- `insert_device` accepts native Live device UI names on Live 12.3+. Plug-ins and Max devices continue to use browser / `.adg` workflows.
- `get_simpler_sample` and `set_simpler_sample_window` use integer sample frames. `replace_simpler_sample` requires Live 12.4+.
- `apply_note_modifications` merges partial patches by `note_id`, preserving omitted fields and updating supported velocity, probability, and MPE fields in place.
- `get_application_info` and `press_current_dialog_button` operate through the Remote Script. The latter requires the 9877 socket to already be bound; it cannot dismiss a startup dialog that prevents that socket from opening. See [MCP_ISSUES.md](MCP_ISSUES.md).

## Updating the Remote Script

When you modify any file in `AbletonMCP_Remote_Script/`, deploy the entrypoint together with its imported modules (`control_surface.py`, `support.py`, `plugin_params.py`, and `mixins/`):

```bash
python tools/deploy_remote_script.py
python tools/launch_ableton.py --reload
```

The source package is intentionally split into a tiny `__init__.py` entrypoint, `control_surface.py`, shared `support.py`, and command-domain mixins. See [DEVELOPMENT.md](DEVELOPMENT.md) for the full module layout and command workflow.

## AI Melody Generation

`tools/midigenai_bridge.py` is a CLI that pipes Ableton clip notes through
the [midigenai](https://github.com/nicholasbien/midigenai) package
(v2 model, weights on
[huggingface.co/nicholasbien/midigenai](https://huggingface.co/nicholasbien/midigenai))
to generate melody continuations. The agent reads a clip with
`get_clip_notes`, shells out to the bridge, and writes the result back with
`add_notes_to_clip` — no MCP server changes needed. See
[tools/README.md](tools/README.md) for setup, dependencies, and usage.

## Timing and recording gotchas (Live 12, measured)

- **Live auto-arms every new track.** An armed MIDI track with Monitor In in arrangement record mode records over its clip instead of playing it, so a master resample with instrument tracks left armed is silent. `resample_master` disarms everything but its own recorder; do the same in scripts.
- **`Song.back_to_arranger` is True while session clips override the arrangement.** `play_arrangement` / `set_back_to_arranger` set it False (what the Back to Arrangement button does); the older code set True and, with record mode on, recorded silence over every track.
- **Socket readings of `current_song_time` go stale under recording load** (a reading 15 bars behind was seen); never time anything from them. MIDI clock out of an IAC port is what fluidclaude follows.
- **External MIDI into Live lands ~32 ms late** on tracks that monitor input (IAC transit plus Live's input latency at 512 samples; only ~3 ms on tracks with monitoring Off, because Live shifts recorded MIDI by the monitoring latency). fluidclaude's `latency auto` measures and cancels it.
- **Audio into Live through BlackHole needs one aggregate device** (BlackHole + interface, one clock source, drift correction on BlackHole) as both Live's input and output, with the BlackHole output pair disabled in Output Config. With BlackHole as input and another device as output the audio arrives 100-200 ms late with ±50 ms jitter; with Main Out on the BlackHole pair, Live feeds back into itself. Setup details: fluidclaude's docs/live-setup.md.
- **Changing Live's audio preferences while a script is creating tracks crashed Live.** Stop scripting first.
- **Recording files are finalized late.** A recorded clip's AIFF gets its real header only when the clip is finalized, and the file is deleted if its track is deleted first; read the PCM after the size settles and before deleting the track.

## Known Limitations

- **Arrangement editing has a bounded LOM surface** — Direct audio/MIDI clip insertion, inline MIDI notes, readback, and deletion are supported; higher-level timeline operations remain unavailable.
- **Session-view audio clips** — `ClipSlot.create_clip()` only accepts a length (for MIDI clips), not file paths, so samples can only be placed in the arrangement (`create_arrangement_audio_clip`).
- **No audio export** — Live has no export command; `resample_master` records the main mix through a Resampling track instead.
- **Set and track structure control** — The public LOM does not expose save-set, insert-time, or track reparent/create-group operations.
- **Analysis and routing gaps** — Sidechain source selection and LUFS/true-peak analysis are not exposed.
- **Stale song reference** — First command after an Ableton restart may fail (retry works). The script auto-refreshes its internal reference.
- **Startup dialogs** — `press_current_dialog_button` cannot help until the Remote Script has already bound port 9877; a crash-recovery or Save Untitled dialog that blocks binding must be handled outside this command path.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for the module layout, threading model, adding new commands, device parameters, automation, and recording architecture.

## License

MIT — see [LICENSE](LICENSE).

**Built with** [Model Context Protocol](https://github.com/modelcontextprotocol) and [Ableton Live](https://www.ableton.com).
