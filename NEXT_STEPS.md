# Next Steps

## Implemented in this worktree

- [x] MCP server and Remote Script workflows for tracks, clips, devices, mixer, scenes, transport, automation, browser access, and arrangement read/write operations.
- [x] Direct arrangement audio/MIDI clip insertion, inline MIDI notes, arrangement readback, clip deletion, and timed session-scene recording.
- [x] Group/return/master robustness, return-track lifecycle, device bypass, clip editing, routing, monitoring, and master resampling.
- [x] Recording safeguards: bar-aware timing, auto-disarm, cancellation, arrangement playback, and stale-song refresh.
- [x] Capture MIDI: `capture_midi(destination)` with 0=auto, 1=session, 2=arrangement.
- [x] Append notes to existing session or arrangement MIDI clips via `add_notes_to_clip` (`arrangement_clip_index`).
- [x] Clip envelopes on session or arrangement clips (`arrangement_clip_index` on get/set/clear).
- [x] Capture and insert scene, crop clip, clip launch mode/quantization/legato.
- [x] Groove pool list/apply/clear and `song.groove_amount`.
- [x] Rack chain list/insert (Live 12.3+), chain mixer, macro **values** (mapping a parameter onto a macro remains GUI-only).
- [x] MIDI-effect loading via existing browser load + `move_device` (Remote Script).
- [x] Compressor sidechain source get/set when the device exposes `input_routing_type`.
- [x] Cue points, crossfader, `show_view`, warp-marker get/add.
- [x] Browser `user_folders` Places roots (Remote Script; folder must be a Live Place).
- [x] MCP-capable-agent documentation: provider-neutral `AGENTS.md`, Claude adapter guidance, exact `.claude/skills/` / `.agents/skills/` mirrors, and the mirror checker.

## Remaining work

### Public LOM limits
- The public Live LOM has no save-set, insert-time, or track-reparent/create-group operation.
- `user_folders` only lists Places the user added; `AudioAssets` is not a built-in category and is Max-backend unavailable.
- Creating a **new** macro map is GUI-only; `get_rack_macros` / `set_device_parameter` only read and set existing macros.
- Audio-to-MIDI slicing has no public “Slice to New MIDI Track” command.
- LUFS / true-peak analysis is not in the Live API; use an external meter or analyze a `resample_master` file outside Live.
- Live has no general export command; use `resample_master` for a recorded mixdown.
- Validate backend-specific browser and arrangement behavior before relying on a workflow.

### Still unresolved
- [ ] Macro **mapping** (Map mode is GUI-only)
- [ ] Audio-to-MIDI slicing
- [ ] Clipless arrangement automation lanes (clip-tied envelopes now work)
- [ ] Follow actions, clip colors, start/end markers, warp-marker move/delete, clip fades
- [ ] Freeze/flatten, duplicate scene, cue volume, take lanes, annotations

See [MISSING_FEATURES.md](MISSING_FEATURES.md) for the compact categorized list.
