# Agent workflow

This repository exposes Ableton Live through an MCP server and supports MCP-capable agents.

- Keep provider-neutral project guidance here; provider adapters may add local instructions.
- Use uv run (or the project virtual environment) for Python commands and keep Live-connected checks explicit.
- Skills are mirrored byte-for-byte in .claude/skills/ and .agents/skills/; run python tools/check_skill_mirrors.py after skill edits.
- Keep changes focused, preserve concurrent work, and update documentation when capabilities or limitations change.

Useful check:

    python tools/check_skill_mirrors.py