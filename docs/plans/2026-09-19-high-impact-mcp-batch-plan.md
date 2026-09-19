# High-Impact MCP Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize the 20 provider skill mirrors, document provider-neutral MCP-capable-agent workflows, and align capability docs with current code and Live LOM limits.

**Architecture:** `.claude/skills/` remains Claude’s discovery tree; `.agents/skills/` is the exact provider-neutral mirror for Codex and other agents. Root guidance lives in `AGENTS.md`, with `CLAUDE.md` containing only Claude-specific adapter context; a standalone checker validates the two trees.

**Tech Stack:** Markdown, Python 3 standard library, Git worktree.

**Spec:** `docs/plans/2026-09-19-high-impact-mcp-batch-spec.md`

## Global Constraints

- Do not edit `.claude/skills` bodies or implementation code.
- Do not modify or canonize `.agents/mcp_config.json`.
- Preserve concurrent disjoint edits and work only in the linked worktree.
- Do not commit or spawn subagents.
- Run only `python tools/check_skill_mirrors.py` for validation.

## Review Focus

- Missing mirror file: the checker must name the missing relative path.
- Extra mirror file: the checker must reject an unexpected relative path.
- Changed mirror content: the checker must reject byte differences.
- Provider ambiguity: docs must distinguish canonical `AGENTS.md` guidance from the `CLAUDE.md` adapter.
- Capability drift: docs must not claim save-set, insert-time, reparent/create-group, sidechain-source, LUFS/true-peak, or Capture MIDI support.

### Task 1: Exact Skill Mirrors

**Files:**
- Create or preserve: `.agents/skills/*/SKILL.md` for the 20 matching Claude skills.
- Reference only: `.claude/skills/*/SKILL.md`.

**Interfaces:**
- Consumes: the 20 existing Claude `SKILL.md` files.
- Produces: an identical relative-path and byte-content set under `.agents/skills/`.

- [ ] Confirm the two roots contain the same 20 `SKILL.md` relative paths.
- [ ] Confirm every corresponding file has identical bytes without changing either skill body.

### Task 2: Provider-Neutral Documentation

**Files:**
- Modify: `AGENTS.md`, `CLAUDE.md`, `README.md`, `SKILL_AUTHORING_GUIDE.md`, `DEVELOPMENT.md`.

**Interfaces:**
- Consumes: current MCP server capabilities and existing project guidance.
- Produces: canonical provider-neutral workflow plus a Claude adapter and consistent discovery statements.

- [ ] Keep `AGENTS.md` concise and provider-neutral.
- [ ] Keep `CLAUDE.md` Claude-specific and explicitly subordinate to `AGENTS.md`.
- [ ] State MCP-capable-agent support, Claude `.claude/skills/` discovery, Codex `.agents/skills/` discovery, and exact mirror checking in the requested docs.
- [ ] Remove stale statements that direct arrangement clips are read-only.

### Task 3: Mirror Validation

**Files:**
- Modify or preserve: `tools/check_skill_mirrors.py`.

**Interfaces:**
- Consumes: both skill roots relative to the repository root.
- Produces: exit code `0` plus a concise count when equal, otherwise exit code `1` plus missing, extra, or differing relative paths.

- [ ] Ensure missing roots/files are reported as failures.
- [ ] Ensure unexpected files in either tree are reported as failures.
- [ ] Ensure byte differences are reported as failures.
- [ ] Keep the success output concise and count the checked `SKILL.md` files.

### Task 4: Capability Baseline and Handoff

**Files:**
- Modify: `MISSING_FEATURES.md`, `NEXT_STEPS.md`.
- Create: `docs/plans/2026-09-19-high-impact-mcp-batch-spec.md`, `docs/plans/2026-09-19-high-impact-mcp-batch-plan.md`.
- Read only: `H:\gitprojects\ableton-mcp-pro\MCP_ISSUES.md`.

**Interfaces:**
- Consumes: current MCP server/Remote Script behavior and the parent issue notes.
- Produces: compact, evidence-based implemented/remaining capability lists and the four-task planning handoff.

- [ ] Mark current arrangement, recording, group/return/master, routing, monitoring, clip-editing, and resampling capabilities as implemented.
- [ ] Do not claim Capture MIDI unless a current MCP tool exposes it.
- [ ] Record the save-set, insert-time, track-reparent/create-group, browser user-folder/`AudioAssets`, sidechain source, and LUFS/true-peak limitations.
- [ ] Run exactly `python tools/check_skill_mirrors.py` and preserve its exact result for handoff.
