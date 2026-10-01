# Missing Features

Capabilities that are not implemented, not fully functional, or blocked by the public Live LOM. Remaining-work list: [NEXT_STEPS.md](NEXT_STEPS.md). MCP faults: [MCP_ISSUES.md](MCP_ISSUES.md).

## Public Live LOM (cannot implement)

- No save-set, insert-time, or track-reparent/create-group operation.
- No LUFS / true-peak / spectrum / GR meter; no monitor-audio stream. `output_meter_level` misses short transients.
- No general export; `resample_master` is a resampling-track recording, not an export command.
- Individual Drum Rack sample loading requires Live 12.4+ (`insert_chain`,
  `DrumChain.insert_device`, and `Simpler.replace_sample`). `load_drum_pad_sample`
  supports empty pads on those versions. No public Slice-to-MIDI-Track.
- Creating a **new** rack macro map is GUI-only (`set_device_parameter` can only set existing macros).
- Arrangement clip envelopes: `automation_envelope` / `create_automation_envelope` are session-only. Arrangement automation is track-level and not in the LOM.
- Live will not place an instrument before MIDI effects.
- `clip.groove = None` (and `0` / `False`) is not a valid Python groove handle. Max can use `id 0`; Python cannot. New MIDI clips still report `has_groove: true`.
- Live 12 Song: no setter for `count_in_duration` / `exclusive_arm` on this build.
- VST/AU internals: unmapped knobs are not in the LOM (Configure panel only, ~128 cap; no one-click add-all). Serum `.serumpreset` files are not host program banks. Live does not group Configure sliders (MCP infers groups from names).
- Browser `user_folders` lists Places roots only (not a built-in category). Absent if the user never added that Place.

## Wired but not functional

| Command | Why it is not done |
|---------|-------------------|
| `clear_clip_groove` | Cannot assign a null `TPyHandle<AAbstractGroove>` from Python. `apply_groove` works. |
| `set_count_in_duration` | Property has no setter. |
| `set_exclusive_arm` | Property has no setter. |
| `set_clip_envelope` on arrangement clips | LOM session-only; command errors by design. |

Auto start/end warp “shadow” markers refuse `move_warp_marker` / `delete_warp_marker`. User-added markers work.

## LOM exists, no MCP tool yet

### Clip
| Feature | LOM |
|---------|-----|
| Follow actions | `clip.follow_action_*` (version-dependent; may not be exposed) |
| Clip fades | fade in/out (arrangement audio) |
| Clip scrub | `clip.scrub` / `stop_scrub` |

### Song / transport
| Feature | LOM |
|---------|-----|
| Scrub by | `song.scrub_by` |
| Global swing if distinct from groove amount | `song.swing_amount` |

### Tracks / scenes / mixer
| Feature | LOM |
|---------|-----|
| Freeze / flatten | often not in the public LOM |
| Track delay | often not exposed |
| Pre/post fader send mode | send mode toggle |

### Devices / Live 12 / other
| Feature | LOM |
|---------|-----|
| Plugin windows | show/hide floating GUI (LOM from Live 12.4.3; not on 12.3) |
| Take lanes | Live 12+ |
| MIDI transformations | Live 12 MIDI tools |
| Clipless arrangement automation | no song-level automation-lane object |
| Annotations | clip / track info text |
| Listeners | `add_*_listener()` |
