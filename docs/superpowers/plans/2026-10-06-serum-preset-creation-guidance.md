# Serum 2 Preset Creation Guidance Implementation Plan

**Goal:** Make requested new Serum sounds lead to complete offline preset creation.

**Architecture:** Extend bundled Markdown sections and existing MCP discovery
instructions; keep the codec and public tool signatures unchanged.

**Spec:** ../specs/2026-10-06-serum-preset-creation-guidance.md

**Execution:** Inline, auto-accepted per user instructions; focused checks and one
final review. Preserve concurrent edits; no commits or per-task review loops.

## Tasks

- [x] Expand `serum-presets.md` with a creation contract, full design checklist,
  fixture-derived module map and coherent editing examples.
- [x] Route new-preset requests to those sections from overview, Serum controls,
  MCP tool instructions/docstrings, both synth skill mirrors, AGENTS/CLAUDE and README.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_sound_design.py
  tests/test_serum_presets.py -q` and the skill mirror checker. Review all edited
  instruction surfaces for consistency once the request is implemented.

## Review focus

Offline creation must not require a running Live instance. A dry-run must not
count as delivery. Unknown asset descriptors and modulation IDs must not be
invented. New designs must change their defining sound architecture while
retaining legitimate baseline settings. File success must not imply live loading.

## Results

Project Python lacked pytest; `uv run --with pytest python -m pytest
tests/test_sound_design.py tests/test_serum_presets.py -q` passed (29 tests).
Skill mirror check passed (21 skills). Final self-review corrected the conversion
SHA256 instructions, limited Live prerequisites to live work and reconciled
encoded-file versus manual-instance handoffs. Three checked binary/JSON pairs
matched decoded state. No agent behavior simulation, live loading or audition
was performed; these remain outside this instruction-change validation.

## Existing-preset transformation follow-up

- [x] Add `existing-preset-edits` with adjective interpretation, current-source
  identification, the full JSON round trip and decoded verification contract.
- [x] Route imperative edit requests from MCP tool descriptions/responses,
  synth guides, both skill mirrors, agent guidance and README.
- [x] Validate offline guide/preset tests and skill mirrors, then review the
  complete follow-up for targeted edits, per-input hashes and explicit live limits.

Follow-up validation: 29 offline tests passed; 21 skill mirrors matched;
`existing-preset-edits` retrieved successfully through the MCP guide function.
Final self-review distinguished the JSON transformation sequence from the general
new-design workflow. Agent behavior/live loading/audible results remain untested.
