# Agent workflow

This repository exposes Ableton Live through an MCP server. Keep guidance provider-neutral, preserve concurrent work, and keep changes focused.

## Serum 2 manual-settings handoff

- Whenever designing or editing a Serum 2 patch, **always include a `Serum 2 — manual settings` section in the final chat response**. A file, issue log, or generic statement that controls are missing does not replace this handoff.
- Read the target instance's unfiltered `get_device_parameters` inventory before editing. Configure mappings differ between instances; host-reported names are not proof a control is writable. Check write results/readback and include skipped or failed intended settings in the handoff.
- Identify the track name/index, device index, and patch role. List **every intended setting not applied through MCP**, with its Serum UI location, exact desired value/selection and units, and status `not applied — set manually`. Keep verified MCP-applied settings separate. Never present desired manual values as observed current values or claim the patch is complete while manual steps remain.
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
