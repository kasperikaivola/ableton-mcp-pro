# Missing Features

Current unresolved or uncertain capabilities. Implemented work is listed in [NEXT_STEPS.md](NEXT_STEPS.md).

## Limitations (public Live LOM)

- No save-set, insert-time, or track-reparent/create-group operation.
- Browser `user_folders` lists Places roots on the Remote Script only. `AudioAssets` appears only if the user added it as a Place; the Max backend has no browser.
- Creating a new rack macro **map** is GUI-only. Macro **values** are readable/settable (`get_rack_macros`, `set_device_parameter`).
- LUFS and true-peak analysis are not in the Live API; external metering or analysis of a `resample_master` file is required.
- Live has no general export command; `resample_master` records the main mix through a resampling track.
- Remote Script and Max for Live backends do not expose identical browser and arrangement capabilities.

## Still unimplemented

Compact list of LOM capabilities that exist but are not MCP tools yet. Do not treat this as a claim that every item is equally feasible.

### Clip editing
| Feature | LOM API |
|---------|---------|
| Quantize pitch | `clip.quantize_pitch` |
| Clip color / mute | `clip.color`, `clip.muted` |
| Start/end markers | `clip.start_marker`, `clip.end_marker` |
| Per-clip time signature | `clip.signature_numerator` / `signature_denominator` |
| Follow actions | `clip.follow_action_*` (version-dependent) |
| RAM mode | `clip.ram_mode` |

### Audio clips
| Feature | LOM API |
|---------|---------|
| Warp marker move/delete | `move_warp_marker` / `delete_warp_marker` |
| Clip fades | fade in/out properties |
| Beat/sample conversion | `beat_to_sample_time`, `sample_to_beat_time` |

### Song / transport
| Feature | LOM API |
|---------|---------|
| Tap tempo / jump / scrub | `tap_tempo`, `jump_by`, `scrub_by` |
| Global swing | `song.swing_amount` (groove amount is implemented) |
| Count-in, exclusive arm, punch in/out | `count_in_duration`, `exclusive_arm`, `punch_in` / `punch_out` |
| Session record / automation record | `session_record`, `session_automation_record` |
| Re-enable automation | `song.re_enable_automation()` |
| Global scale | `scale_name` / `scale_intervals` |
| Continue playing | `song.continue_playing()` |

### Tracks / scenes / mixer
| Feature | LOM API |
|---------|---------|
| Track / scene color | `color` / `color_index` |
| Track freeze / flatten | `track.freeze()`, `track.flatten()` |
| Track delay | per-track delay compensation |
| Scene tempo / time signature / duplicate | `scene.tempo`, `duplicate_scene` |
| Cue volume | `mixer_device.cue_volume` |
| Pre/post fader sends | send mode toggle |

### Devices, racks, groove
| Feature | LOM API |
|---------|---------|
| Macro mapping | Map mode is GUI-only |
| Plugin windows / presets | show/hide GUI, store/recall banks |
| Simpler sample window | `simpler.sample`, start/end |
| Audio-to-MIDI slicing | no public Slice-to-MIDI-Track command |

### View / Live 12 / other
| Feature | LOM API |
|---------|---------|
| Take lanes | Live 12+ take-lane management |
| MIDI transformations | Live 12 MIDI tools |
| Clipless arrangement automation | no song-level automation-lane object |
| Annotations | clip / track info text |
| Application info | `app.get_major_version()` etc. |
| Listeners | `add_*_listener()` |

## Implemented in this batch

- Direct arrangement audio/MIDI clip insertion, inline MIDI notes, readback, and deletion.
- `add_notes_to_clip` appends to session or arrangement MIDI clips (`arrangement_clip_index`).
- Arrangement recording timing safeguards, auto-disarm, cancellation, and playback.
- Group/return/master handling, return-track lifecycle, device bypass, clip editing, routing, monitoring, and master resampling.
- Capture MIDI (`capture_midi`) and capture-and-insert-scene.
- Clip crop, launch mode/quantization/legato, groove pool, rack chains (Live 12.3+ insert), chain mixer, macro values.
- MIDI effects via `load_instrument_or_effect` + `move_device` (Remote Script).
- Compressor sidechain routing, cue points, crossfader, `show_view`, warp-marker get/add.
- Clip envelopes on arrangement clips; browser `user_folders` Places (Remote Script).
- Provider-neutral MCP-capable-agent documentation and exact `.claude/skills/` / `.agents/skills/` mirrors with a checker.
