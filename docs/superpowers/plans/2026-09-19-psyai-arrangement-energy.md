# Psy AI Arrangement Energy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Increase disciplined full-on energy, phrase-level variation, psychedelic SFX detail, and clarity of the beat-352 transition without destabilizing the dark low end.

**Architecture:** Add independent upper-percussion, drum-fill, glide, and Saturn-processed glitch-melody layers around the existing arrangement. Resolve tracks by name before every mutation because creating or duplicating tracks changes numeric indices. Preserve original tracks or clips before destructive note removal, then verify every layer through arrangement queries, MIDI-note reads, and brief playback-meter passes.

**Tech Stack:** Ableton Live at 145 BPM, abletonmcp arrangement and device tools, Serum 2, existing Drum Rack and FX Rack, FabFilter Saturn 2, flattened Ableton Samples catalog.

**Spec:** docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md

## Global Constraints

- Preserve the dark night-psy identity.
- Make one subtle development every 8 bars and one recognizable fill or transition every 16 bars.
- Do not use dense 2-4-bar micro-editing.
- Do not add Saturn 2 to the master or permanently process the main bass full-band.
- Keep the beat-350-to-352 interval free of progressive-bass and dark-motif MIDI notes.
- Keep glide gestures occasional and use note velocities from 118 through 127.
- Preserve clearly named muted backups before destructive edits.
- Resolve current track indices by exact track name immediately before each mutation.
- The user must save the Live set manually because the MCP has no save command.

## Review Focus

- Track insertion shifts indices: each mutating task must re-query names and refuse to use a stale index.
- Sample loading may not create a playable Simpler device: verify the new track has a loadable instrument and audible meter activity before programming the full hat arrangement.
- Added bass gestures can mask the kick or main bass: restrict glide clips to designated transition windows and meter them in context.
- Long notes may leak into the two-beat vacuum: read both edited clips and assert no note intersects clip-relative beats 126-128.
- VST controls may not be exposed: use only visible parameters and leave detailed Serum or Saturn internal settings for manual UI adjustment.

---

### Task 1: Capture Baseline and Create Safety Backups

**Files:**
- Reference: docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md
- Reference: MCP_ISSUES.md

**Interfaces:**
- Consumes: current Live set with tracks named Dark Progressive Bass, Dark Phrygian Motif, Serum Glide Bass, 1-Drum Rack, FX Rack, and Serum Glitchy Distorted Melody.
- Produces: muted backup tracks for the two clips that will be destructively edited, plus a verified name-to-index map.

- [ ] **Step 1: Verify global state**

Call get_session_info and get_arrangement_info. Require tempo 145, time signature 4/4, record mode off, and arrangement playback active rather than Session override.

- [ ] **Step 2: Resolve all target tracks by name**

Call get_track_info for the current track count and record the live indices for the six named targets. Ignore group-track endpoint errors; do not infer neighboring indices.

- [ ] **Step 3: Verify source clips**

Call get_arrangement_clips for Dark Progressive Bass and Dark Phrygian Motif. Require exactly one active arrangement clip on each, starting at beat 224 and ending at beat 352.

- [ ] **Step 4: Duplicate destructive-edit targets**

Duplicate each target track. Immediately rename and mute the duplicates:

- BACKUP Dark Progressive Bass pre-energy-pass (MUTED)
- BACKUP Dark Phrygian Motif pre-energy-pass (MUTED)

Re-resolve every target index after each duplication.

- [ ] **Step 5: Verify backups**

Read both backup tracks and their arrangement clips. Require mute=true and the original 224-352 clip on each.

### Task 2: Build an Independent Upper-Percussion Energy Layer

**Files:**
- Reference: docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md

**Interfaces:**
- Consumes: sample URI query:Samples#FileId_2027 for Hihat Closed Alien Spawn 1.wav.
- Produces: MIDI track Alien Hat Energy with four controlled 8-bar arrangement clips.

- [ ] **Step 1: Create and name the MIDI track**

Create a MIDI track at the end and rename it Alien Hat Energy. Set its initial volume to 0.55 and leave panning centered.

- [ ] **Step 2: Load the approved hat sample**

Load query:Samples#FileId_2027 onto Alien Hat Energy. Query the track afterward and require at least one playable instrument device.

- [ ] **Step 3: Probe the root note**

Create a one-beat arrangement clip at beat 60 with one MIDI note: pitch 60, start 0, duration 0.125, velocity 80. Play briefly from beat 60 and require nonzero track meter output. Delete this probe clip after verification.

- [ ] **Step 4: Program the four energy blocks**

Create 32-beat clips at beats 96, 160, 384, and 448. In every beat of each clip, place pitch 60 at offsets 0.5 and 0.75 with duration 0.10. Alternate velocities 66 and 78; raise the final two hits of each 8-bar clip to 88 and 102.

- [ ] **Step 5: Verify placement and level**

Read all four clips and require 64 notes per clip, exact 32-beat lengths, and no notes outside their clip bounds. Play one first-full-on block and one returning-full-on block; keep meter peaks below the kick and bass tracks. Reduce track volume to 0.48 if it dominates.

### Task 3: Create the Glide Gestures and Two-Beat Vacuum

**Files:**
- Reference: docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md

**Interfaces:**
- Consumes: active tracks Serum Glide Bass, Dark Progressive Bass, and Dark Phrygian Motif.
- Produces: four short glide clips and a silent low-end/motif window from beat 350 through beat 352.

- [ ] **Step 1: Program transition glide clips**

Create two-beat arrangement clips on Serum Glide Bass at beats 134, 190, 348, and 478. Each clip uses overlapping notes:

    pitch 42, start 0.00, duration 1.25, velocity 120
    pitch 49, start 1.00, duration 0.60, velocity 127
    pitch 43, start 1.45, duration 0.55, velocity 124

- [ ] **Step 2: Verify glide timing**

Read each glide clip and require three notes, all velocities in the 118-127 range, and no note extending past the two-beat clip.

- [ ] **Step 3: Remove the last two progressive-bass beats**

On the active Dark Progressive Bass arrangement clip, remove all pitches from clip-relative time 126 for a span of 2 beats. Do not edit the muted backup.

- [ ] **Step 4: Remove the last two motif beats**

On the active Dark Phrygian Motif arrangement clip, remove all pitches from clip-relative time 126 for a span of 2 beats. Do not edit the muted backup.

- [ ] **Step 5: Verify the vacuum**

Read both clips. Require that no note starts in or sustains into clip-relative beats 126-128. Confirm the arrangement still contains the existing sub rise, sucking effect, final-beat kick roll, alien hit, and full-on bass start at beat 352.

- [ ] **Step 6: Meter the transition**

Play from beat 346 through beat 356. Verify the glide track is active during beats 348-350, both edited musical tracks are silent during 350-352, and the rolling full-on bass meters from beat 352.

### Task 4: Add a Dedicated Drum-Fill and Accent Layer

**Files:**
- Reference: docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md

**Interfaces:**
- Consumes: devices and known MIDI lanes from 1-Drum Rack; pitch 38 is the existing rapid rhythm lane and pitch 40 is the proven drop accent.
- Produces: track Drum Fills & Accents containing only phrase-boundary additions.

- [ ] **Step 1: Duplicate and isolate the Drum Rack**

Duplicate 1-Drum Rack, rename the copy Drum Fills & Accents, and set volume to 0.58. Query its arrangement clips, then delete every copied clip in descending index order.

- [ ] **Step 2: Add subtle 8-bar accents**

Create 0.25-beat clips at beats 96, 160, 384, and 448. Each contains pitch 40 at start 0, duration 0.25, with velocities 72, 78, 82, and 88 respectively.

- [ ] **Step 3: Add major 16-bar fills**

Create two-beat clips at beats 126, 190, 350, 414, and 478. Each contains:

    pitch 38, start 1.00, duration 0.125, velocity 55
    pitch 38, start 1.25, duration 0.125, velocity 68
    pitch 38, start 1.50, duration 0.125, velocity 84
    pitch 38, start 1.75, duration 0.125, velocity 106
    pitch 40, start 1.75, duration 0.25, velocity 112

- [ ] **Step 4: Verify disciplined spacing**

Read the track arrangement. Require four subtle accents and five major fills only; there must be no continuous clip and no extra event every 2-4 bars.

- [ ] **Step 5: Meter fills in context**

Play around beats 126-129, 350-353, and 414-417. If the duplicate rhythm lane causes obvious meter spikes above the main Drum Rack, reduce the fill track volume to 0.50 rather than changing the main drum level.

### Task 5: Vary Psychedelic SFX and Use the Existing Saturn Chain

**Files:**
- Reference: docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md

**Interfaces:**
- Consumes: FX Rack known lanes 38, 40, 41, 43, 44, and 48; empty Serum Glitchy Distorted Melody with Serum 2 followed by Saturn 2.
- Produces: varied major-boundary dark glitch phrases and three non-identical replacement FX phrases in the returning full-on section.

- [ ] **Step 1: Verify Saturn availability**

Read Serum Glitchy Distorted Melody devices and require Serum 2 followed by Saturn 2, both enabled. Confirm the Arpeggiator remains bypassed. Do not change internal Saturn bands or modulation because only Device On and Input Gain are exposed.

- [ ] **Step 2: Program Saturn-processed glitch phrases**

Create one-beat clips on Serum Glitchy Distorted Melody at beats 128, 192, 352, 416, and 480. Each phrase uses:

    pitch 54, start 0.00, duration 0.125
    pitch 55, start 0.25, duration 0.125
    pitch 60, start 0.50, duration 0.125
    pitch 54, start 0.75, duration 0.125

Use base velocities 88, 78, 84, and 96. Add 0 at beat 128, 6 at beat 192, 14 at beat 352, 10 at beat 416, and 8 at beat 480, clamping every result to 127. Leave Serum Laser unchanged.

- [ ] **Step 3: Back up the FX Rack**

Duplicate FX Rack, rename the duplicate BACKUP FX Rack pre-energy-pass (MUTED), and mute it. Re-resolve the active FX Rack index.

- [ ] **Step 4: Replace repeated returning-full-on phrases**

Query active FX Rack arrangement clips and identify clips by start time, not stored index. Replace only the clips starting at beats 412, 444, and 476:

    beat 412, length 6:
      pitch 45 at 0.00, pitch 40 at 1.50, pitch 43 at 3.50, pitch 48 at 5.50

    beat 444, length 6:
      pitch 41 at 0.00, pitch 45 at 2.00, pitch 38 at 4.50

    beat 476, length 6:
      pitch 44 at 0.00, pitch 43 at 1.50, pitch 40 at 3.50

Use duration 0.25 for every note and velocities between 82 and 108, with the last note in each phrase loudest.

- [ ] **Step 5: Verify variation**

Read the three replacement clips and compare them with neighboring clips. Require different pitch sequences and event timings so the returning full-on FX no longer repeats the same two-note phrase every 16 beats.

- [ ] **Step 6: Meter Saturn and FX layers**

Play around beats 412-418 and 444-450. Ensure the Saturn-processed glitch melody and FX Rack events are audible but do not sustain across the next kick-and-bass phrase.

### Task 6: Final Arrangement Verification and Handoff

**Files:**
- Modify if new failures occur: MCP_ISSUES.md

**Interfaces:**
- Consumes: all clips and tracks produced by Tasks 1-5.
- Produces: verified live arrangement and a concise user handoff.

- [ ] **Step 1: Verify the phrase grid**

List arrangement clips for the new upper-percussion, glide, drum-fill, Serum Glitchy Distorted Melody, and active FX Rack tracks. Confirm subtle events align to 8-bar boundaries and major events to 16-bar boundaries.

- [ ] **Step 2: Verify rollback assets**

Confirm all three backup tracks are muted and retain their source clips:

- progressive bass backup
- dark motif backup
- FX Rack backup

- [ ] **Step 3: Perform three playback checks**

Play and stop each region separately:

- beats 92-132 for first-full-on growth
- beats 346-360 for the two-beat vacuum and full-on return
- beats 380-452 for returning-full-on progression

Record meter snapshots for main Drum Rack, rolling/full-on bass, upper percussion, drum fills, glide bass, Serum Glitchy Distorted Melody, and FX Rack.

- [ ] **Step 4: Apply only gross-level corrections**

If a new layer clearly exceeds its anchor track, lower that new layer. Do not raise the master, main kick, or main bass during this pass.

- [ ] **Step 5: Update MCP issue documentation**

Append any newly encountered inability to MCP_ISSUES.md, including the intended action, exact endpoint failure, and workaround used or why no workaround was safe.

- [ ] **Step 6: Hand off for listening**

Report every track and beat range changed, identify all muted backups, remind the user to save manually, and ask for listening feedback on energy, density, and the beat-352 transition before any mix-bus processing.
