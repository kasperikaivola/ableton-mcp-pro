---
name: synth-sound-design
description: Design new Serum 2 or Omnisphere sounds and suggest improvements to existing synth tracks. Use for mystical FX, fuller textures, custom patches, synth sound design, or flat/bland synthesizer sounds with partial manual controls.
---

# Synth Sound Design

Use alongside genre skills for Serum 2/Omnisphere synthesis decisions and complete
manual handoffs. This skill does not grant extra editing permission.

## Read the references

Call `get_synth_sound_design_guide(synth="overview", section="workflow")` first.
Read `checklist`, `values` and `handoff` as needed, then the chosen synth's
`identity` and relevant control sections, or `section="all"`. `index` lists IDs.
References work offline without a Live connection. If the tool is unavailable:

- [Workflow and handoff](../../../MCP_Server/synth_guides/overview.md)
- [Serum 2 controls and recipes](../../../MCP_Server/synth_guides/serum2.md)
- [Omnisphere controls and recipes](../../../MCP_Server/synth_guides/omnisphere.md)

Paths are relative to this mirrored skill directory. Reload the MCP server to
discover the tool. Do not substitute Serum 1 controls or infer Omnisphere version.

## Context and choice

For a file-only Serum preset request, skip Live session/device reads and go
directly to **Complete Serum preset files** below. No running instance is needed.
Use these context steps when the request involves a running instrument/song.

1. Read `get_session_info`, target/neighbor `get_track_info`, relevant arrangement,
   clips and notes. Infer role, harmony, register and gaps with confidence.
2. Identify the actual instrument, track/device and nested rack chain if needed.
   For Omnisphere identify version, Part, Layer(s), MIDI channel and output.
3. Read the instance's **unfiltered** `get_device_parameters` before edits.
   Configured knobs, host names, MIDI Learn and full GUI state are distinct.
4. Prefer Serum 2 for precise animated timbres and Omnisphere for organic/sample
   hybrids; honor the requested synth or preserve the existing instrument.
5. State evidence/assumptions. Names/MIDI do not prove unheard timbre. Unseen
   sources, FX, library availability and routes remain unknown/unverified.

## New sound requests

“Add a new mystical FX synth” authorizes creating/loading that sound. Inspect
context, explain its role, find a real browser item/URI, create/name a MIDI track,
load the instrument and verify its resulting device list. `insert_device` is for
native Live devices; VSTs use browser/rack tools. Recheck indices after changes.
Never fabricate a URI or internal preset name. Browser support depends on backend.

Inspect the new inventory; do not assume Init. Design the full patch using the
references' checklist. Apply only controls with verified mappings/conversions;
read back writes/display values. If loading/initialization is blocked, give exact
manual steps and accurately report the partial result.

For Serum 2, implement that design in a separate `.SerumPreset` with the offline
workflow below. Missing Configure controls are not a reason to leave sources,
filters, envelopes, matrix or FX unedited. Generate the file even if loading is
blocked. Load before live adjustments that would be replaced by preset loading.

Include inactive module states or a confirmed baseline, exact sources/modes,
routing, envelopes, modulation, FX order/values/sync, voices/performance and save
dependencies. Add an audition clip if useful, based on reliable harmony; preserve
existing material and avoid casual transport/global tempo changes.

## Existing patch requests

“Make this Serum preset faster/darker/bouncy”, “edit this preset” and equivalent
imperative requests authorize actual file edits. Read `serum-presets` section
`existing-preset-edits`; identify the existing source/current export, unpack the
complete `.SerumPreset` to disk JSON with `convert_serum_preset`, edit a separate
JSON (using `edit_serum_preset` with `output_format="json"` or a lossless local
script), then repack a separate `.SerumPreset`. Inspect each input's own SHA256.
Compare original versus output for intended changes and edited JSON versus output
for decoded equality. Deliver the edited file, not only a recipe or Configure
writes. Preserve patch identity, unrelated settings and originals; do not Init.
Interpret adjectives from the actual patch/context, explain the chosen changes
and ask only for essential unresolved ambiguity. Faster is not permission to
change song tempo. A same-named file is not a loaded instance's unsaved state;
if current state cannot be exported automatically, request that missing export.
Opaque non-JSON CBOR uses the disclosed guarded binary fallback; never discard it.

“Suggest changes” is **read-only**. Keep preset, clips, automation and routing;
propose one coherent improvement plus optional alternatives. Explicit requests
to apply changes permit targeted writes/readback; record before values. Never
initialize or replace the original patch to fit a reference recipe.

Separate observations from hypotheses. Explain each change's purpose and give
exact before/target values where observed; otherwise state prerequisites and
desired endpoints. Ask for a name/screenshot only when an important unknown
requires it. Give conditional ideas without inventing readback. Match level and
audition in context before judging audible results.

## Final chat contract

Provide the full patch/change recipe **in chat**, with identity, role, rationale,
assumptions and verified writes. Include a `Serum 2 — manual settings` or
`Omnisphere — manual settings` section per instance; identify Omnisphere version,
Part/Layer/FX rack and slot. Every intended unapplied setting belongs in this table:

| Section / control | Desired value or selection (units) | Status |
|---|---|---|
| Exact UI location and route | Exact source/mode/value/endpoints | not applied — set manually |

Cover source names/paths, position/warp, FX type/order/enable/sync and all other
missing controls. Modulation needs source -> destination, base/endpoints,
depth/polarity, waveform, rate, sync and retrigger/loop. Automation needs its
time/value curve and a statement that it has not been implemented; static values
cannot substitute for it. Put initialization before dependent manual steps.

If all intended changes were verified, still include the section with
`No manual settings required for the verified changes.` Otherwise retain gaps.
User-confirmed values are not MCP-verified without readback. Mark unconfirmed
assets as proposed choices, availability unknown/unverified. Do not claim a
complete patch while manual steps remain.

## Complete Serum preset files

For hidden Serum state, read `get_synth_sound_design_guide(synth="serum-presets", section="workflow")`
and its `new-preset-design`, `module-editing`, `tools-and-paths`,
`editing-semantics` and `preservation-and-handoff` sections.
Read `complete-state-recipes` for FX, matrix, wavetable/assets, curves and every
other decoded module. These file edits are available even when live readback or
audition is pending. Never interpret missing Configure knobs as missing JSON access.
Use `edit_serum_preset` `copy` operations with `from` and `path`, and the inspected
`source_file_path`/`source_sha256` pair for reference files, to transfer complete
subtrees including embedded data without copying previews. Object destinations
set/replace, array destinations insert (`/-` appends); reconcile dependent routes
and selectors explicitly. Copying does not invent/remap enum or module IDs.

**Create a new preset means actually write a new `.SerumPreset`, not only a
recipe, renamed template, minor knob edit or dry-run.** Use a validated Init or
suitable template and compatible reference modules. Plan and perform substantial
style-defining edits across oscillator mode/wavetable selection/warp/unison,
sub/noise, filters/routing, amplitude and additional envelopes, LFO curves/rates,
matrix/performance routes, ordered/repeated FX with their settings, and voicing.
For every category record edit, retain from named baseline (reason), off/unused,
or a specific blocker. Do not enable every module or invent unknown enum IDs.

Use complete inspected asset descriptors, FX slots and modulation relationships
when reusing reference state; reconcile coupled fields and destination addressing.
An envelope/LFO or macro without its routes does not implement modulation.
Finish independent supported edits when a particular mapping/asset is unknown.
For file-only requests, there is no Live inventory prerequisite. For live patch
edits inspect the instance before writes and distinguish exported from unsaved state.

Use `get_serum_preset_info`, bounded `read_serum_preset` / `search_serum_preset`,
SHA256-guarded `edit_serum_preset` to separate outputs, `convert_serum_preset`
for full disk JSON extraction/packaging and `compare_serum_presets` for decoded
verification. Never feed huge embedded sample arrays to chat or write summary
previews back as complete state. Discover real paths; unknown file defaults,
enums, units and coupled fields need verified mappings or controlled manual exports.
A disk preset is not loaded-instance readback. File generation preserves unknown
fields/assets but loading and auditioning remain manual. Keep this distinction in
the final manual-settings handoff, including unapplied loading/verification steps.
For authorized creation, dry-run then publish with `dry_run=false` and compare
decoded edits against the complete design, including dependent routes and FX order.
Report output path and dependencies, verified file edits, live loading status and
specific gaps. Settings encoded in a verified file need loading, not redundant
manual recreation; identify them as encoded but not applied to the instance.

## Preset and asset discovery

Use `search_audio_assets` before guessing a template/preset path. Default root is
`G:/AudioAssets`; `*init*.SerumPreset` or `*pad*.SerumPreset` searches filenames
at every depth, and `**/Serum*/**/*.SerumPreset` narrows folder patterns. Matching
is case-insensitive; use next_offset and respect scan_complete/stop_reason/errors.
Narrow root_path to a discovered pack for faster scans. Validate candidates with
get_serum_preset_info. Legacy .fxp is discoverable but not editable by our Serum 2
codec. Filesystem paths are not Ableton browser URIs or Serum internal asset names.
