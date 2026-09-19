# Psy AI Breakdown and Sound Dialogue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark, atmospheric 24-bar breakdown from beats 352-448, add composed call-and-response exchanges throughout both drops and the progressive section, and reduce mud in the full-on Dark Rolling Bass.

**Architecture:** Work directly in the open Ableton Live set through abletonmcp. Preserve the stable kick-bass foundations, place new MIDI gestures on existing dedicated FX/fill tracks, and organize the breakdown as six four-bar stages. Resolve track and arrangement-clip indices immediately before every destructive edit because Live renumbers them after duplication or deletion.

**Tech Stack:** Ableton Live, abletonmcp, Serum 2, Omnisphere, FabFilter Saturn 2, Ableton Drum Rack, Glue Compressor, and EQ Eight.

**Spec:** `docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md`

## Global Constraints

- Keep the dark night-psy identity; do not restore the uplifting Happy Melody material.
- Preserve the active Dark Progressive Bass from beats 224-352 and Dark Rolling Bass from beat 448 onward.
- Use subtle development every 8 bars and recognizable fills or transitions every 16 bars.
- Put question and answer sounds in separate gaps; avoid simultaneous low-frequency statements.
- Leave beats 446-448 mostly empty before the full-on return.
- Keep Serum Laser unchanged.
- Create clearly named muted backups before destructive edits or processor changes.
- The MCP cannot save the Live set or monitor its audio; the user saves and makes final sonic judgments in Live.

## Current Track Map

- Track 0: `1-Drum Rack`
- Track 1: `Drum Fills & Accents`
- Track 3: `Dark Rolling Bass`
- Track 4: `Dark Progressive Bass`
- Track 8: `Omni Alien SFX`
- Track 10: `Omni Sucking Bass`
- Track 12: `Omni Sub Annihilator`
- Track 13: `Fall FX`
- Track 14: `Serum Braam`
- Track 15: `Serum Glitchy Distorted Melody`
- Track 16: `Serum Glide Bass`
- Track 18: `FX Rack`
- Track 26: `Dark Phrygian Motif`
- Track 28: `Serum 2nd Melody`
- Track 30: `Alien Hat Energy`

Treat these indices as a snapshot only. Re-resolve names after every track duplication.

## Review Focus

- Track indices may shift after backup duplication; re-read names before every later mutation.
- Arrangement clip indices may shift after insertion or deletion; refresh the target track immediately before editing a clip.
- The final two-beat vacuum can be defeated by looping drum clips or long note tails; inspect every active clip crossing beats 446-448.
- Call-and-response can become clutter if both voices overlap; verify each pair has deliberate temporal separation.
- EQ Eight frequency values are normalized and the MCP cannot audition the result; use conservative settings and retain an instant muted backup for A/B listening.

---

### Task 1: Refresh the Live Set and Create Rollback Points

**Files:**
- Modify: the open `PsyAI Test Project` Ableton Live set
- Reference: `docs/superpowers/specs/2026-09-19-psyai-arrangement-energy-design.md`

**Interfaces:**
- Consumes: current Live arrangement after the user's inserted time and track renames
- Produces: verified track map, current clip indices, and a muted Dark Rolling Bass backup

- [ ] **Step 1: Refresh session and track identities**

Call `get_session_info`, then `get_track_info` for the tracks listed in Current Track Map. Record names and mute states. If any name/index differs, use the returned name as authority and update all subsequent calls.

- [ ] **Step 2: Refresh relevant arrangement clips**

Call `get_arrangement_clips` for tracks 0, 1, 3, 4, 8, 10, 12, 13, 15, 16, 18, 26, 28, and 30. Confirm:

- Dark Progressive Bass occupies beats 224-352.
- The breakdown window is beats 352-448.
- Serum 2nd Melody starts at beat 384.
- Dark Rolling Bass starts at beat 448.

- [ ] **Step 3: Duplicate the Dark Rolling Bass**

Use `duplicate_track` on the freshly resolved Dark Rolling Bass index. Rename the duplicate `BACKUP Dark Rolling Bass pre-cleanup (MUTED)` and mute it. Re-read the track list because all later indices may have shifted.

- [ ] **Step 4: Confirm rollback safety**

Verify the active Dark Rolling Bass is unmuted, the backup is muted, and both contain identical arrangement clips before processing changes.

### Task 2: Add Progressive-Drop Variation and Dialogue

**Files:**
- Modify: arrangement beats 224-352 on `Drum Fills & Accents`, `Omni Alien SFX`, `Serum Glitchy Distorted Melody`, `Serum Glide Bass`, and `FX Rack`

**Interfaces:**
- Consumes: active Dark Progressive Bass and Dark Phrygian Motif, existing FX Rack events every four bars
- Produces: restrained 8-bar variation and four recognizable question/answer exchanges

- [ ] **Step 1: Read reusable source gestures**

Use `get_arrangement_clip_notes` on one current clip from each of `Omni Alien SFX`, `Serum Glitchy Distorted Melody`, `Serum Glide Bass`, `FX Rack`, and `Drum Fills & Accents`. Reuse known triggering pitches and note lengths; do not guess new Drum Rack pads.

- [ ] **Step 2: Add subtle 8-bar drum punctuation**

Create short clips on `Drum Fills & Accents` at beats 256 and 320. Use one restrained percussion hit or a two-hit pickup with velocities below the major fills. Do not add duplicate full-strength kicks.

- [ ] **Step 3: Add the first two conversational pairs**

Create a short high or midrange question near beat 248 and a contrasting answer near beat 252. Create a second pair near beats 280 and 284 using different tracks, preferably FX Rack followed by Omni Alien SFX. Keep each voice shorter than one beat.

- [ ] **Step 4: Strengthen the midpoint event**

Around beat 288, preserve the existing alien event and add a stronger drum fill immediately before it. Let the alien sound act as the answer; do not stack an additional low impact on the same beat.

- [ ] **Step 5: Add the final progressive conversation**

Create a short FX or glitch question around beat 312 and an answer around beat 316. Preserve the existing glide at beats 348-350, the fill at beats 350-352, and the bass/motif vacuum at beats 350-352.

- [ ] **Step 6: Structural checkpoint**

Refresh the affected tracks. Confirm no new clip masks the Dark Progressive Bass, all pairs alternate rather than overlap, and no added note enters beats 350-352 except the approved transition FX/fill.

### Task 3: Compose Breakdown Stages 1-3

**Files:**
- Modify: arrangement beats 352-400 on `Omni Alien SFX`, `Fall FX`, `FX Rack`, `Serum Glitchy Distorted Melody`, and `Dark Phrygian Motif`

**Interfaces:**
- Consumes: existing alien hit at beat 352, fall tail at beat 350, FX Rack event near beat 366, and Serum 2nd Melody beginning at beat 384
- Produces: decompression, suspended atmosphere, and the first melodic conversation

- [ ] **Step 1: Preserve the opening impact and clear space**

Keep the existing Omni Alien SFX event at beat 352 and Fall FX tail. Do not introduce kick, rolling bass, or continuous sub during beats 352-368.

- [ ] **Step 2: Build a sparse first exchange**

Use the existing FX Rack event near beat 366 as one side of a dialogue. Add one short contrasting response one to two beats later on Serum Glitchy Distorted Melody or Omni Alien SFX. Keep the total active time below two beats.

- [ ] **Step 3: Create suspended atmosphere at beats 368-384**

Add two isolated events separated by at least four beats. Use a short Dark Phrygian Motif fragment as the question and a non-pitched FX Rack or alien response. Avoid a regular drum pulse in this stage.

- [ ] **Step 4: Introduce Serum 2nd Melody without masking it**

At beats 384-400, leave the first chord attack exposed. Add one motif or glitch question after the chord has settled, followed by a contrasting answer before beat 400. Keep both responses in gaps and avoid long notes that cross the next chord boundary.

- [ ] **Step 5: Structural checkpoint**

Confirm stages 1-3 contain no Dark Rolling Bass or full drum groove, and verify no added MIDI note overlaps the Serum 2nd Melody chord changes at beats 384 and 400.

### Task 4: Compose Breakdown Stages 4-6 and the Drop Vacuum

**Files:**
- Modify: arrangement beats 400-448 on `Omni Sub Annihilator`, `Drum Fills & Accents`, `1-Drum Rack`, `Alien Hat Energy`, `Omni Sucking Bass`, `Serum Glide Bass`, `FX Rack`, and melodic FX tracks

**Interfaces:**
- Consumes: Serum 2nd Melody, existing FX Rack events near beats 400, 432, and 444, and the user's current drum clip at beats 432-448
- Produces: rising rhythmic tension, four-bar final build, and a mostly empty beats 446-448

- [ ] **Step 1: Add restrained low punctuation at beats 400-416**

Read an existing Omni Sub Annihilator clip and reuse its proven pitch. Create no more than two short or decaying sub events, placed away from the Serum chord attack. Pair one with a high glitch response.

- [ ] **Step 2: Begin the pulse at beats 416-432**

Create sparse percussion on `Drum Fills & Accents`: begin with one pulse per bar, then increase to one pulse every two beats during the second half. Add sparse hats only after the pulse is established.

- [ ] **Step 3: Inspect the existing beats 432-448 drum build**

Read the current `1-Drum Rack` clip notes. If it already accelerates appropriately, preserve it and add only complementary hats or accents. If it is a static loop, delete that single arrangement clip and recreate a 14-beat explicit build from beats 432-446 using only proven kick/percussion pitches.

- [ ] **Step 4: Add the final conversational escalation**

Use three increasingly close exchanges across beats 432-446: an FX question with percussion answer, a glitch question with low response, then a glide or sucking-bass question that leads into the vacuum. Increase velocity and reduce the time between voices without stacking them.

- [ ] **Step 5: Create the final vacuum**

Ensure no drum, hat, sub, motif, glitch, or glide MIDI begins during beats 446-448. Allow only the approved sucking/riser tail if it enhances tension and does not fill the low end continuously.

- [ ] **Step 6: Confirm the full-on landing**

Verify Dark Rolling Bass and the main full-on drum groove begin together at beat 448. Keep the existing drop accent at beat 448 and avoid adding multiple redundant impacts.

### Task 5: Extend Call-and-Response Through Both Full-On Drops

**Files:**
- Modify: arrangement beats 64-192 and 448-576 on `Serum Glitchy Distorted Melody`, `Omni Alien SFX`, `FX Rack`, `Drum Fills & Accents`, and optionally `Serum Glide Bass`

**Interfaces:**
- Consumes: established sound pairings from Tasks 2-4
- Produces: a recurring conversational identity inside both drops

- [ ] **Step 1: Select three reusable pairings**

Use these families consistently: high glitch answered by low alien/sub punctuation; Phrygian or tonal fragment answered by percussion; broad fall/braam gesture answered by sucking or glide bass. Exclude any pairing whose source sound feels bright or euphoric.

- [ ] **Step 2: Place exchanges in the first full-on**

Add sparse pairs near beats 96/100, 128/132, and 160/164. Treat beat 128 as the strongest event. Leave other phrase endings unanswered.

- [ ] **Step 3: Place exchanges in the returning full-on**

Add related but evolved pairs near beats 480/484, 512/516, and 544/548. Keep beat 512 strongest and use different answers from the first drop so the second section progresses.

- [ ] **Step 4: Protect the low end**

Do not place Omni Sub Annihilator, sucking bass, or glide notes over dense rolling-bass passages unless the event is shorter than two beats and occupies a deliberate bass dropout.

- [ ] **Step 5: Structural checkpoint**

Inspect all six pairs. Confirm each question precedes its answer, voices do not accidentally overlap, and no active exchange repeats more frequently than once per eight bars.

### Task 6: Clean Up Dark Rolling Bass

**Files:**
- Modify: devices on active `Dark Rolling Bass`
- Preserve: `BACKUP Dark Rolling Bass pre-cleanup (MUTED)`

**Interfaces:**
- Consumes: active Serum 2 -> Glue Compressor -> EQ Eight chain
- Produces: conservative, reversible low-mid cleanup for user A/B evaluation

- [ ] **Step 1: Re-read processor parameters**

Call `get_device_parameters` for Serum 2, Glue Compressor, and EQ Eight on the freshly resolved active Dark Rolling Bass index. Confirm EQ Eight is off, Glue range is 70 dB, sidechain remains enabled, and Serum Macro 1 is near 0.94.

- [ ] **Step 2: Enable conservative EQ cleanup**

Turn on EQ Eight. Preserve band 1's existing low-cut type and set its normalized frequency near 0.05, corresponding approximately to 28-30 Hz. Use band 2 as a broad bell near normalized frequency 0.33, approximately 180-220 Hz, with gain around -2.5 dB and moderate Q. Leave output gain at 0 dB.

- [ ] **Step 3: Limit compression range**

Set Glue Compressor Range to approximately 6 dB, normalized about 0.086 instead of 1.0. Preserve sidechain on, dry/wet at 100%, makeup at 0 dB, and the existing threshold initially.

- [ ] **Step 4: Leave the unknown Serum macro unchanged**

Do not alter Macro 1 during this pass because the MCP cannot identify its mapping. If the bass remains muddy after EQ and compression A/B, ask the user to test Macro 1 around 0.75 manually inside Serum.

- [ ] **Step 5: Prepare A/B listening**

Confirm the active track and muted backup have identical clips and levels. Tell the user to alternate their mute states in Live while auditioning the first and returning full-on sections; only one version should be audible at a time.

### Task 7: Final Arrangement Audit and Handoff

**Files:**
- Modify if necessary: `MCP_ISSUES.md`
- Inspect: the open Ableton Live set

**Interfaces:**
- Consumes: all arrangement and processing changes from Tasks 1-6
- Produces: structurally coherent project ready for subjective audition and manual save

- [ ] **Step 1: Refresh all affected clips**

Query arrangement clips for every modified track. Confirm the breakdown occupies beats 352-448, the progressive bass ends at 352, and the full-on bass begins at 448.

- [ ] **Step 2: Audit phrase boundaries**

Check subtle events at 8-bar boundaries, major events at 16-bar boundaries, all question/answer ordering, and the beats 446-448 vacuum.

- [ ] **Step 3: Run short transport auditions**

Play and stop three windows: beats 240-296 for progressive variation, beats 344-456 for the full breakdown/drop arc, and representative windows in both full-on drops. Use transport only to expose gross routing or silence problems; do not claim subjective sonic success.

- [ ] **Step 4: Record MCP limitations**

If any intended action cannot be completed through abletonmcp, append the exact desired action, failure, and workaround to `MCP_ISSUES.md`. Do not duplicate limitations already documented.

- [ ] **Step 5: Handoff for listening and saving**

Report the precise musical changes, identify the A/B backup track, ask the user to judge breakdown pacing, sound dialogue, drop impact, and bass clarity, and remind them to save the Live set manually.

