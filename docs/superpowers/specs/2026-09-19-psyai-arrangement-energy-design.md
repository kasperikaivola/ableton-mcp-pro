# Psy AI Arrangement Energy Design

## Objective

Increase the track's energy, progression, and psychedelic detail without losing its dark night-psy identity. The arrangement should remain disciplined and hypnotic: subtle development every 8 bars, a recognizable fill or transition every 16 bars, and enough restraint that major events retain impact.

## Current Structure

- Beats 0-64: intro.
- Beats 64-192: first full-on section.
- Beats 192-224: breakdown and transition.
- Beats 224-352: dark progressive section.
- Beats 352-480: returning full-on section.
- Beats 480 onward: closing section.

The kick and bass already meter strongly. The anemic impression is therefore treated primarily as an arrangement and spectral-motion problem, not a request for indiscriminate level increases.

## Energy Strategy

Use an arrangement energy ladder:

- Every 8 bars: one subtle change, such as a percussion accent, short FX response, brief glide gesture, or restrained rhythmic variation.
- Every 16 bars: one clearly recognizable fill, dropout, or transition event.
- Preserve long stable stretches between events so the groove remains hypnotic.
- Prioritize both full-on sections, where the lack of upper-percussion motion and evolving accents is most noticeable.

Dense micro-editing every 2-4 bars is explicitly out of scope.

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

## 2:25 Transition

The transition at beat 352 currently contains a 16-beat sub rise, a two-beat sucking effect, a final-beat kick roll, an alien hit, and a drop accent. It feels sudden because the progressive bass and motif continue underneath the buildup until the handoff.

Rebuild the final four beats as follows:

- Beats 348-350: one high-velocity Serum glide phrase.
- Beats 350-352: remove progressive bass notes and dark-motif notes to create a two-beat vacuum.
- Continue the existing sub rise and sucking effect through the vacuum.
- Preserve the existing kick roll during the final beat.
- Beat 352: land the returning full-on bass with the alien hit and existing extra percussion accent.
- Add at most one additional dark impact or processed FX accent; do not stack redundant impacts.

## Full-On Progression

First full-on section:

- Beat 64: establish the core groove.
- Beats 96 and 160: subtle percussion or FX development.
- Beat 128: stronger 16-bar fill or glide response.
- Beat 190-192: major transition into the breakdown.

Returning full-on section:

- Beat 352: strongest return, but retain room for later growth.
- Beat 384: subtle accent or upper-percussion addition.
- Beat 416: stronger fill and optional glide response.
- Beat 448: final energy lift through percussion or short psychedelic FX.
- Beat 478-480: major exit fill into the closing section.

## Safety and Rollback

- Preserve original musical tracks whenever destructive edits are required by keeping clearly named muted backups.
- New fills, glide phrases, and processed FX should live on dedicated tracks where practical.
- Do not alter the muted original bright progressive bass or full Happy Melody backup.
- Do not save over the Live set automatically; the MCP lacks a save command, so the user must save manually after auditioning.

## Verification

- Confirm all new clips start and end on intended phrase boundaries.
- Verify the beat 350-352 bass and motif vacuum contains no unintended MIDI notes.
- Confirm the full-on bass resumes at beat 352.
- Briefly meter each new layer during playback to catch silent clips or gross level mismatches.
- Audition the first full-on, the 2:25 transition, and the returning full-on in Live.
- Success means greater perceived energy and progression without constant fills, euphoric harmony, or a destabilized low end.
