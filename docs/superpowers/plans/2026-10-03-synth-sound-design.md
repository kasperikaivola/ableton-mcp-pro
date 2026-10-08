# Synth Sound Design Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with focused
> checks and one whole-request review under the user's AGENTS instructions.

**Goal:** Make context-aware Serum 2/Omnisphere design and improvement recipes
available to repository agents and external MCP clients.

**Architecture:** Package Markdown references with the MCP server and expose a
read-only retrieval tool. A mirrored skill and plug-in reminders route agents to
the references; existing tools perform authorized Live operations.

**Tech Stack:** Python, FastMCP, Markdown; no new production dependencies.

**Spec:** `docs/superpowers/specs/2026-10-03-synth-sound-design.md`

## Global constraints

- Preserve concurrent work; work inline in this clean feature checkout.
- Keep testing minimal and focused; review after the entire implementation.
- Reference content works offline; no Live command changes.
- Desired manual settings are never presented as observed or applied values.

## Review focus

- Unknown version or installed assets: mark unverified and provide confirmation.
- Suggest-only existing patch requests: do not mutate or initialize the patch.
- Empty Configure list or renamed plug-in: still route to guide and handoff.
- Invalid synth/section/path input: return allowed choices, never arbitrary files.
- Installed package: references and tool subpackages must be in the wheel.

## Tasks

1. [x] Write overview and both control references with vendor citations,
   version boundaries, patch completeness checklist and original recipes in
   `MCP_Server/synth_guides/{overview,serum2,omnisphere}.md`.
2. [x] Implement `MCP_Server/tools/sound_design.py`, register it in
   `MCP_Server/tools/__init__.py`, and link from plug-in parameter responses in
   `devices_browser.py`. Add only the server tool to the command-surface baseline.
3. [x] Add mirrored `.agents/skills/synth-sound-design/SKILL.md` and
   `.claude/skills/synth-sound-design/SKILL.md`; update AGENTS.md, CLAUDE.md,
   README.md and authoring guidance for explicitly hybrid manual workflows.
4. [x] Configure setuptools package discovery/data in `pyproject.toml` so tools
   and references are shipped; add focused `tests/test_sound_design.py` checks.
5. [x] Run focused tests, skill mirror check, `git diff --check`, and inspect
   built wheel contents. Review the whole request once and fix material findings.

No Live session is edited to test a documentation feature. Record verification
results below when complete.

## Verification results

- 27 focused tests passed: guide retrieval/aliases/errors/offline registration,
  plug-in response reminders, command surfaces and production source size.
- 21 skill mirrors match; local guide/skill/README links resolve; diff check clean.
- Wheel build passed; inspected all guide/tool package entries and retrieved the
  Omnisphere guide from an isolated wheel import.
- One bounded Luna whole-request review: no material findings.
- No Live edits or audible verification performed. Existing MCP connections need
  reload to discover the new server tool; no Remote Script deployment is required.
- Omnisphere modern vendor-guide access was blocked; legacy control facts and
  current product feature families are scoped explicitly, with exact modern
  labels/ranges requiring confirmation. No claim of exhaustive current-build UI
  verification is made.
