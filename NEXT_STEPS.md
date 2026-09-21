# Next Steps

Remaining work only. Catalog of gaps: [MISSING_FEATURES.md](MISSING_FEATURES.md). MCP faults: [MCP_ISSUES.md](MCP_ISSUES.md).

## Public LOM limits

- No save-set, insert-time, or track-reparent/create-group.
- No LUFS / true-peak / spectrum / GR meter; no general export (`resample_master` is a recording workaround).
- No load-sample-onto-drum-pad; no public Slice-to-MIDI-Track.
- New rack macro **maps** are GUI-only.
- Arrangement clip envelopes and clipless arrangement automation are not in the LOM.
- Live will not place an instrument before MIDI effects.
- Python cannot assign a null clip groove handle (`clear_clip_groove`).
- `count_in_duration` / `exclusive_arm` have no setter on this Live 12 Song.
- `user_folders` lists Places roots only.

## Unresolved

- [ ] Macro **mapping** (Map mode is GUI-only)
- [ ] Audio-to-MIDI slicing
- [ ] `clear_clip_groove` (null groove handle)
- [ ] `set_count_in_duration` / `set_exclusive_arm` (no setter)
- [ ] Arrangement clip envelopes / clipless arrangement automation
- [ ] Follow actions, clip fades, freeze/flatten, take lanes, annotations
- [ ] Plugin windows (Live 12.4.3+ LOM)
- [ ] `song.scrub_by`, clip scrub, send pre/post, listeners
