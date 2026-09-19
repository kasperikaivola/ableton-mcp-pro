# High-Impact MCP Batch Specification

## Goal

Make the repository’s provider-neutral agent workflow explicit, keep Claude and Codex skill discovery synchronized, and rebaseline capability documentation against the current MCP implementation and researched Live LOM limits.

## Scope and constraints

- Work only in the assigned worktree and owned paths.
- Mirror all 20 `.claude/skills/*/SKILL.md` files byte-for-byte into `.agents/skills/*/SKILL.md`; do not edit either skill body.
- Treat `AGENTS.md` as the provider-neutral contract and `CLAUDE.md` as the Claude adapter.
- State that MCP-capable agents are supported, Claude discovers `.claude/skills/`, Codex discovers `.agents/skills/`, and both trees are checked by `tools/check_skill_mirrors.py`.
- Do not modify or canonize `.agents/mcp_config.json`.
- Read the parent `MCP_ISSUES.md` only for context; do not edit it.
- Do not change implementation code, commit, or spawn subagents.

## Four-task structure

### Task 1: Exact skill mirrors

Provide all 20 matching `SKILL.md` files under `.agents/skills/` with content identical to `.claude/skills/`.

### Task 2: Provider-neutral documentation

Keep the root `AGENTS.md` concise and canonical, make `CLAUDE.md` an adapter, and align `README.md`, `SKILL_AUTHORING_GUIDE.md`, and `DEVELOPMENT.md` with both provider discovery paths and MCP-capable-agent support.

### Task 3: Mirror validation

Ensure `tools/check_skill_mirrors.py` fails for missing, extra, or content-different `SKILL.md` files and prints a concise success summary.

### Task 4: Capability baseline and handoff

Rebaseline `MISSING_FEATURES.md` and `NEXT_STEPS.md` against current code, record the researched limitations, and save this specification plus its implementation plan. The required limitations are: no public Live LOM save-set, insert-time, or track-reparent/create-group operation; uncertain user-folder/`AudioAssets` browser exposure; and future sidechain source plus LUFS/true-peak analysis.

## Acceptance criteria

- The mirror checker reports success for 20 files.
- No `.claude/skills` body is changed.
- Provider-neutral and Claude-specific responsibilities are unambiguous.
- Capability docs do not claim unsupported operations.
- Capture MIDI is documented as implemented (`capture_midi`).
