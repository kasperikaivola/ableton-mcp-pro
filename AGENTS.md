# Agent workflow

This repository exposes Ableton Live through an MCP server. Keep guidance provider-neutral, preserve concurrent work, and keep changes focused.

## Synth sound design

- Discover nested presets/assets with `search_audio_assets` (default root `G:/AudioAssets`): filename wildcards search every depth; path wildcards support `**`. Follow pagination, respect incomplete scan flags and validate Serum preset candidates before edits. Returned file paths are not browser URIs; legacy `.fxp` is discoverable but unsupported by the Serum 2 file editor.

- For new Serum 2/Omnisphere sounds or improvements to existing synth tracks, read the [synth-sound-design skill](.agents/skills/synth-sound-design/SKILL.md) and `get_synth_sound_design_guide` (overview workflow, then selected synth controls/recipes). The offline references are in [MCP_Server/synth_guides](MCP_Server/synth_guides/overview.md).
- For live sound work, inspect song/track/device context and the instance's unfiltered parameter inventory. File-only Serum creation uses the exported template/reference state and does not require Live. Separate observations, inferred roles and proposed values; track names/MIDI are not evidence of unheard timbre or hidden GUI state.
- New sound requests authorize creation/loading with existing tools. Suggestion-only requests are read-only; preserve the existing patch and automation. Apply targeted changes only when requested. Verify the resulting device and parameter readback; report partial results accurately.
- Choose between the user's installed Serum 2 and Omnisphere based on role; never invent a browser URI, internal preset/source name, normalized conversion or opaque FX mapping. Confirm version and asset dependencies before relying on them.
- Omnisphere designs/edits require the same final-chat handoff as Serum below, titled `Omnisphere — manual settings`, identifying version (or unknown/unverified), Part, Layer and FX rack/slot. List every intended unapplied setting with exact UI location, value/selection/units, routing and `not applied — set manually`. Keep verified MCP writes separate.
- Include the complete patch/change recipe in chat. Inaccessible modulation/automation needs full source/destination/timing/depth or time/value curves and remains unimplemented until applied. Do not claim a finished patch while manual steps remain.

## Serum 2 manual-settings handoff

- For complete offline Serum preset state, read `get_synth_sound_design_guide(synth="serum-presets", section="workflow")`. Use bounded preset read/search tools, SHA256-guarded edits to separate outputs and decoded comparison. Preserve unknown fields/assets, never write previews back as complete modules, and do not claim file generation applied to the loaded instance. Unknown file enums/defaults/units require verified mapping or controlled manual exports.
- New Serum preset requests authorize **actually writing a separate `.SerumPreset`** with the offline tools. Read `new-preset-design` and `module-editing`; deliberately implement style-defining source/wavetable, sub/noise, filter/routing, envelope/LFO, modulation/performance, ordered FX and voicing changes. Record each category as edited, intentionally retained from a named baseline, off/unused or specifically blocked. Missing Configure controls do not block offline creation; file-only requests need no Live connection. Do not stop at a recipe, renamed template or dry-run. Compare the published file against the design; keep loading/auditioning and any true gaps explicit.
- Read `complete-state-recipes` for FX/matrix/wavetable and all other decoded-state edits. Use guarded `edit_serum_preset` `copy` operations (`from`, `path`, optional reference `source_file_path` plus required `source_sha256`) to transfer complete subtrees/assets without using previews. Reconcile selectors and dependent routes explicitly; copy does not remap IDs. Pending live readback/audition limits verification claims, not file-editing access.
- Requests like “make this preset faster/darker/bouncy” authorize actual **existing-preset edits**. Read `serum-presets/existing-preset-edits`; identify the file/current export, unpack complete JSON, edit separate JSON and repack a separate `.SerumPreset`, using each input's own SHA256. Compare intended decoded changes and edited-JSON/output equality. Preserve the original, patch identity and unrelated settings; no Init or global tempo change. Suggestions alone remain read-only. Missing current export/identity requires only that clarification; lossless JSON export failure uses the explicitly reported guarded binary fallback.

- Whenever designing or editing a Serum 2 patch, **always include a `Serum 2 — manual settings` section in the final chat response**. A file, issue log, or generic statement that controls are missing does not replace this handoff.
- For live-instance edits, read the target instance's unfiltered `get_device_parameters` inventory before editing. Configure mappings differ between instances; host-reported names are not proof a control is writable. Check write results/readback and include skipped or failed intended settings in the handoff. For offline creation identify the source/output instead; track/device may be not applicable.
- Identify the track name/index, device index, and patch role. List **every intended setting not applied through MCP**, with its Serum UI location, exact desired value/selection and units, and status `not applied — set manually`. Keep verified MCP-applied settings separate. Never present desired manual values as observed current values or claim the patch is complete while manual steps remain.
- Settings encoded and decoded-verified in an output file are file-applied, not live-applied. Group them as `encoded in output; not loaded` with a loading/verification step rather than asking for redundant manual recreation. Still enumerate true unencoded settings/gaps; identify a file-only deliverable without implying it was loaded or auditioned.
- Check these categories for each patch: **wavetables** (oscillator, exact table name/category or user-file path; missing position/warp settings), **FX** (bus, enable/bypass, processing order, effect type and each intended control value, including tempo-sync mode), and **other controls/modulation** (filter/warp modes, routing, voices, source → destination, depth/polarity, rate, sync/retrigger, or any other intended inaccessible setting). Report only the settings needed for the designed patch, not every host parameter.
- Do not confuse wavetable position with wavetable selection. Do not blindly scroll table indices without a reliable selected-name readback. Do not interpret opaque `FX ... Param N` names as known effects. If a label, wavetable availability, current value, or mapping cannot be verified, say `unknown/unverified`, distinguish a proposed choice from a readback, and ask for a screenshot/name confirmation when necessary; do not invent it.
- A static manual setting does not implement time-varying automation. For an inaccessible modulation/automation design, give the manual routing or time/value curve and explicitly state that it has not been implemented.
- If no manual steps are needed for the intended changes, still include the section with `No manual settings required for the verified changes.` If access is uncertain, say so instead of claiming there are no gaps. After the user applies settings, mark them user-confirmed; mark them MCP-verified only when actual readback supports that.

Compact handoff format (one block per Serum instance):

```text
Serum 2 — manual settings
Track: <name> (index <n>), device <n>, role: <bass/lead/pad>
Section / control | Desired value or selection (units) | Status
<Oscillator / FX bus / modulation> | <explicit intended setting> | not applied — set manually
```

## Source layout

- `AbletonMCP_Remote_Script/__init__.py` is the tiny Live entrypoint. `control_surface.py` owns the class, socket, and dispatch; `support.py` contains shared constants/compatibility helpers; `mixins/*.py` contains command-domain implementations.
- `MCP_Server/server.py` is the tiny executable/importable entrypoint. `connection.py` owns TCP policy; `runtime.py` owns the logger, lifespan, and shared `mcp`; `tools/*.py` contains decorated domain tools, registered once by `tools/__init__.py`.
- `MaxForLive/code/lom-handler.js` bootstraps and dispatches. Flat `lom-*.js` files are top-level `include()` modules; `MaxForLive/build_amxd.py` discovers, bundles, and installs all `code/*.js` flat.

## Development

- Add new commands to the matching domain module. Update the Remote Script and Max expectations in `tests/test_command_surfaces.py` only when the public command surface intentionally changes.
- `tests/test_source_layout.py` enforces a 1,000-line ceiling for each production source file.
- Use `uv run` (or the project environment) for Python commands, keep Live-connected checks explicit, and run `python tools/check_skill_mirrors.py` after skill edits.
- Keep `MISSING_FEATURES.md`, `MCP_ISSUES.md`, and `NEXT_STEPS.md` limited to actual missing capabilities, observed faults, and remaining work.
