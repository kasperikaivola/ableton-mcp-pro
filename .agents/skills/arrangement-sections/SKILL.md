---
name: arrangement-sections
description: Create one section in the current arrangement. Use when the user asks for a drop at a position, a 32-bar drop, a breakdown or interlude after the last drop, a buildup at a position, or an intro or outro.
---

# Arrangement Sections

Place one section in the open set. A full song from a loop stays in track-arrangement. When a role has no loop to repeat, the matching genre skill writes the notes.

Do not change tempo. Do not call `record_arrangement` unless session scenes already are this section.

## Locate the range first

Call `get_session_info`, `get_full_arrangement`, and `get_cue_points` before any edit. One Ableton beat is a quarter note. `beats_per_bar = signature_numerator * 4 / signature_denominator` (4/4 → 4, 6/8 → 3).

- "Bar N" is 1-based. Start beat = `(N - 1) * beats_per_bar`. "At beat N" uses N.
- Length = bars × `beats_per_bar`. The user's length wins.
- Omitted length: drop, breakdown, interlude, intro, and outro are 16 bars. A buildup is 8 bars.

"After the last drop" starts at that region's end, snapped up when it is not on a bar: `ceil(end / beats_per_bar) * beats_per_bar`. Find the last drop in order:

1. Latest cue whose name contains "drop". Its region runs to the next cue, or 16 bars when none follows. Cue `time` is in beats.
2. Latest arrangement clip whose name contains "drop".
3. Density: a bar is drop-like when a drum-role track and a bass-role track both cover it. The last contiguous run is the last drop.
4. If none exist, say so and write nothing. An empty set can still take a drop at an absolute bar or beat.

Role comes from the track name, otherwise the instrument: kick, snare, hat, perc, or drum = drums; bass or sub = bass; pad, chord, stab, or keys = harmonic; lead or pluck = lead; fx, riser, noise, or atmos = fx. `get_full_arrangement` lists only tracks that already have arrangement clips (`name`, `start_time`, `end_time`, `length`, `is_midi_clip`, `is_audio_clip`, audio `file_path`). `get_session_info` `track_count` plus `get_track_info` finds empty tracks and session slots. Skip group tracks (`kind: group`).

## Overlap

Arrangement clips cannot be split, moved, or resized. `create_arrangement_midi_clip` fails when its range is not empty.

- Delete a clip with `delete_arrangement_clip` only when it lies wholly inside the range and that track must change. Delete higher indices first. Read its notes first if it is the copy source.
- A clip that starts before the range or ends after it stays. Report it.
- A buildup adds. It does not delete.

## Copying a loop

Same-track session clip, Live 12.3+: `duplicate_clip_to_arrangement(track_index, clip_index, destination_time)` copies notes and envelopes. Tile it at each repeat. If that call fails, `get_clip_notes` and write a new clip.

Arrangement MIDI: `get_arrangement_clip_notes`, then one `create_arrangement_midi_clip`. Note `start_time` is relative to the new clip; add `repeat_index * source_length` for each tile. Audio: `create_arrangement_audio_clip` with that clip's `file_path`.

`set_clip_name` is session-only. Do not claim an arrangement clip was renamed. Optional locator: `set_song_time` to the start beat, then `toggle_cue`. Cue names may not be settable. The clips are the record.

`create_midi_track(-1)` returns a name, not an index. The new track is the last regular track; confirm with `get_track_info` before writing. `create_audio_track(-1)` returns the index. Append only.

Notes are `{pitch, start_time, duration, velocity}`. A 16th note is 0.25 beats. C4 is 60.

## Drop

Full energy. On drum, bass, and harmonic tracks, repeat the fullest 4- or 8-bar loop that already exists (session or arrangement). Do not thin drums. Leave other roles unless a wholly contained clip blocks the rewrite. One crash on beat 1 when `search_audio_assets` returns a `*crash*.wav` or `*impact*.wav` path. Place it with `create_arrangement_audio_clip` on an audio track that is empty at that beat. `create_audio_track(-1)` only when every audio track is blocked there. A role with no loop gets new MIDI from the matching genre skill.

## Breakdown

Keep pads, atmospheres, chords, and fx. Do not place kick or main bass; delete those clips only when they lie wholly inside the range. Last 4 bars, on a snare or clap track that is empty there: 16ths, velocity linear from 40 to 110. Do not shorten the section from a genre guess.

## Interlude

A new sparse part, not a thinned drop. New 2-bar motif on an existing pad or lead, tiled across the range. Half-time kick (hits on beat 1 of each bar only) or no kick. Do not copy the drop bass unchanged. Remove wholly contained kick and main-bass clips in range. If no pad or lead can hold the motif, `create_midi_track(-1)`, `set_track_name` it, and write the motif there.

## Buildup

Add fills, synth notes, and effects on top of the groove.

- Fills: snare or clap 16ths over the last 4 bars (the last 8 when the buildup is 16 bars or more), velocity 40 → 110. Hat 16ths at velocity 70–100 for the whole buildup where that track is empty. `add_notes_to_clip(..., arrangement_clip_index=...)` when a clip already covers the range; otherwise `create_arrangement_midi_clip`.
- Synth: a rising line on an existing lead, or a new MIDI track. 8th notes (duration 0.5) stepping from the section root to root+12. On a new track, `insert_device` (Live 12.3+, native devices) Auto Filter and Reverb, then `get_device_parameters`. Set Frequency near 0.25 and Decay Time near 0.8 with `set_device_parameter` `parameter_name`. For Filter Type, use the normalized value whose `value_items` entry is band-pass or Bandpass. Missing names or items stay unset and are reported.
- Do not call `set_send_level` on a track that also plays outside this range. A new riser track may send to the existing reverb return at 0.7 (`send_index` 0 is return A). Place a crash at the section end (the next downbeat), same sample search as a drop.
- Filter sweeps, send ramps, and volume fades across time are arrangement automation. They are GUI-only. List each curve as a manual step: source, destination, start value, end value, and bar range. Do not claim they were drawn.

## Intro and outro

Intro: drums for the whole section, bass and harmonic parts from the midpoint, one crash on the last downbeat. Outro: harmonic and fx for the whole section, drums and bass for the first half only. Same overlap rules.

## Build order

1. Read session, arrangement, and cues. Compute start beat, end beat, and `beats_per_bar`. Stop when "after the last drop" finds nothing.
2. Classify roles. List wholly contained clips and clips that cross the boundary.
3. Drop, breakdown, interlude, intro, and outro: delete only wholly contained clips on tracks this section changes. A buildup skips deletion.
4. Tile or write clips. Read the source before deleting it.
5. Place the crash when a sample exists and the section asks for one.
6. Re-read `get_arrangement_clips` on each edited track. Report start bar, length, what was written, what was left in place, and any automation still manual.
