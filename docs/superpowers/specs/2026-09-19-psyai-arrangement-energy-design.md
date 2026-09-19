# Psy AI Arrangement Energy Design

## Objective

Increase the track's energy, progression, and psychedelic detail without losing its dark night-psy identity. The arrangement should remain disciplined and hypnotic: subtle development every 8 bars, a recognizable fill or transition every 16 bars, and enough restraint that major events retain impact.

## Current Structure

- Beats 0-64: intro.
- Beats 64-192: first full-on section.
- Beats 192-224: breakdown and transition.
- Beats 224-352: dark progressive section.
- Beats 352-448: 24-bar atmospheric breakdown and build.
- Beats 448-576: returning full-on section.
- Beats 576 onward: closing section.

The kick and bass already meter strongly. The anemic impression is therefore treated primarily as an arrangement and spectral-motion problem, not a request for indiscriminate level increases.

## Energy Strategy

Use an arrangement energy ladder:

- Every 8 bars: one subtle change, such as a percussion accent, short FX response, brief glide gesture, or restrained rhythmic variation.
- Every 16 bars: one clearly recognizable fill, dropout, or transition event.
- Preserve long stable stretches between events so the groove remains hypnotic.
- Prioritize both full-on sections, where the lack of upper-percussion motion and evolving accents is most noticeable.

Dense micro-editing every 2-4 bars is explicitly out of scope.

## Call-and-Response Language

Call-and-response should become a recurring identity in both drops and transitions, not a breakdown-only device.

- Use short, recognizable sound characters: high glitch or melodic question answered by low alien/sub punctuation; Phrygian fragment answered by percussion; braam or falling effect answered by sucking/glide bass.
- Place responses in actual gaps rather than stacking both voices simultaneously.
- Keep the main kick-bass groove stable while the conversation happens mostly in the midrange and high end.
- Use one clear exchange at selected 8-bar boundaries and stronger multi-voice exchanges at 16-bar boundaries.
- Reuse a few pairings across the song so the dialogue feels composed rather than random.
- Leave some phrase endings unanswered to preserve surprise and avoid turning the device into a gimmick.

## Drum Variation

Create a separate layered drum-fill and accent track derived from the existing Drum Rack. This avoids rewriting the main repeating clips and makes the added material independently mutable.

- Use only note lanes already proven to trigger useful sounds because MCP Drum Rack pad inspection currently fails.
- Add restrained accents at 8-bar boundaries.
- Add stronger one-beat or two-beat fills at 16-bar boundaries.
- Velocity-shape repeated hits so rolls accelerate in intensity rather than sounding mechanically flat.
- Avoid layering duplicate full-level kicks over the main kick except where the existing arrangement already creates a dedicated fill window.
- Keep the Drum Rack reverb input low-cut enabled to prevent low-frequency smear.

## Glide Bass

Use the new Serum Glide Bass track as an occasional transition voice, not a continuous layer.

- Program one- or two-beat call-and-response gestures around selected 16-bar boundaries.
- Use high note velocities, approximately 118-127, because the preset appears to respond more convincingly at higher velocity.
- Prefer overlapping notes where a legato glide is desired.
- Keep glide gestures out of sustained kick-and-bass passages when they would mask or destabilize the low end.
- The MCP can program notes and track-level processing but cannot edit Serum's internal oscillator, filter, envelope, mono/legato, or portamento controls.

## Additional SFX

Use the existing MIDI FX Rack and project synth FX first, supplemented by indexed samples only when a usable file path is available.

- Short alien, glitch, zap, reverse, and dark-impact gestures should answer phrase endings rather than play continuously.
- Favor contrasting frequency ranges: high and short details during dense bass passages, and low impacts only at major structural events.
- Avoid stacking several long risers at the same boundary.
- Candidate catalog material includes dark swells, reverse glitches, alien percussion, zaps, and impacts from the flattened Samples catalog.

## FabFilter Saturn 2

Saturn 2 is available at query:Plugins#VST3:FabFilter:Saturn%202.

- Use the existing empty `Serum Glitchy Distorted Melody` track, which already contains Serum 2 followed by Saturn 2, as the primary processed melodic-FX voice.
- Leave `Serum Laser` unchanged because its sound does not suit this arrangement.
- Use Saturn 2 selectively on dedicated glide or FX layers, not on the master and not as permanent full-band processing on the main bass.
- Intended uses are short driven, filtered, or modulated sound-design moments that increase contrast.
- Keep sub frequencies comparatively clean; distortion should emphasize midrange texture and movement.
- If Saturn exposes only generic or limited automation parameters through the MCP, detailed band, modulation, and style settings must be configured manually in the plug-in UI.

## Progressive Drop

Keep the active `Dark Progressive Bass` and `Dark Phrygian Motif` from beats 224-352.

- Add subtle drum or FX variation at beats 256 and 320.
- Add stronger fills and sound conversations around beats 288 and 350-352.
- Let FX questions and answers alternate across phrase gaps; do not cover the continuous bass groove with dense layers.
- Retain the two-beat removal of progressive bass and motif at beats 350-352 as the entrance into the breakdown.

## 24-Bar Breakdown

Use the user-created empty interval from bar 89 to bar 113, beats 352-448. `Serum 2nd Melody` enters at beat 384 and supplies the harmonic atmosphere from the ninth breakdown bar onward.

- Beats 352-368: decompression. Use the existing alien impact and falling tail, followed by spacious low/high FX exchanges.
- Beats 368-384: suspended atmosphere. Keep the spectrum sparse and introduce isolated questions and delayed answers without drums or continuous bass.
- Beats 384-400: let `Serum 2nd Melody` become the center. Place short glitch, alien, or Phrygian answers between its chord changes.
- Beats 400-416: develop the conversation with a second response voice and restrained sub punctuation.
- Beats 416-432: begin rhythmic rebuilding with sparse percussion and an increasingly regular pulse.
- Beats 432-448: create a four-bar escalation using accelerating drums, hats, sucking-bass motion, and a glide-bass tease.
- Leave the final two beats mostly empty so the full-on arrival at beat 448 has physical contrast.
- Keep the harmony dark and ambiguous; do not reintroduce the uplifting Happy Melody material.

## Full-On Progression

First full-on section:

- Beat 64: establish the core groove.
- Beats 96 and 160: subtle percussion or FX development.
- Beat 128: stronger 16-bar fill or glide response.
- Beat 190-192: major transition into the breakdown.

Returning full-on section:

- Beat 448: strongest return, but retain room for later growth.
- Beats 480 and 544: subtle call-and-response or upper-percussion development.
- Beat 512: stronger fill and optional glide response.
- Beats 574-576: major exit fill into the closing section.

## Dark Rolling Bass Cleanup

The full-on `Dark Rolling Bass` uses short, non-overlapping MIDI notes, so note overlap is not the likely source of mud. Its EQ Eight is disabled, Serum Macro 1 is near maximum, and Glue Compressor has an unrestricted 70 dB range.

- Duplicate the track as a clearly named muted backup before processing changes.
- Enable EQ Eight and apply conservative subsonic cleanup plus a modest low-mid reduction, centered approximately in the 150-250 Hz region.
- Restrict Glue Compressor range to roughly 4-6 dB while retaining kick-triggered sidechain behavior.
- Leave Serum Macro 1 unchanged initially because the MCP cannot identify its internal mapping.
- Judge the final EQ and compression by ear in Live; the MCP has no monitor-audio stream.

## Safety and Rollback

- Preserve original musical tracks whenever destructive edits are required by keeping clearly named muted backups.
- New fills, glide phrases, and processed FX should live on dedicated tracks where practical.
- Do not alter the muted original bright progressive bass or full Happy Melody backup.
- Do not save over the Live set automatically; the MCP lacks a save command, so the user must save manually after auditioning.

## Verification

- Confirm all new clips start and end on intended phrase boundaries.
- Verify the beat 350-352 bass and motif vacuum contains no unintended MIDI notes.
- Confirm the breakdown occupies beats 352-448 and the full-on bass resumes at beat 448.
- Confirm question and answer clips alternate rather than overlap accidentally.
- Briefly meter each new layer during playback to catch silent clips or gross level mismatches.
- Audition the progressive section, all six four-bar breakdown stages, both full-on drops, and the returning full-on in Live.
- Success means greater perceived energy and progression without constant fills, euphoric harmony, or a destabilized low end.
