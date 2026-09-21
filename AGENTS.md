# Agent workflow

This repository exposes Ableton Live through an MCP server and supports MCP-capable agents.

- Keep provider-neutral project guidance here; provider adapters may add local instructions.
- Use uv run (or the project virtual environment) for Python commands and keep Live-connected checks explicit.
- Skills are mirrored byte-for-byte in .claude/skills/ and .agents/skills/; run python tools/check_skill_mirrors.py after skill edits.
- Keep changes focused, preserve concurrent work, and update documentation when capabilities or limitations change.

Useful check:

    python tools/check_skill_mirrors.py

# Implementation workflow
1. Implement a set of missing requirements from MISSING_FEATURES.md and/or fix an issue from MCP_ISSUES.md
2. Reload the MCP server
3. Deploy `AbletonMCP_Remote_Script/__init__.py` into Live's MIDI Remote Scripts folder:

       python tools/deploy_remote_script.py

   Discovers Live 12/11 under ProgramData (Windows) or `/Applications` (macOS), copies over `AbletonMCP/__init__.py`, and clears `__pycache__`. Also copies into User Library `Remote Scripts/AbletonMCP` when that folder already exists. Override with `ABLETON_LIVE_ROOT` or `ABLETON_MIDI_REMOTE_SCRIPTS`.
4. Open Ableton Live only if a Live DAW instance is not already running:

       python tools/launch_ableton.py

   Does not start a second instance. After a Remote Script deploy the running process still has the old script; quit Live first or run `python tools/launch_ableton.py --reload` so the new script loads. `--reload` waits until `get_session_info` answers (an open TCP port is not enough).
5. Test all MCP commands the changes affect and verify results (Remote Script on TCP 9877 via MCP tools or `tools/live_client.py`).
6. Update [MISSING_FEATURES.md](MISSING_FEATURES.md), [MCP_ISSUES.md](MCP_ISSUES.md), and [NEXT_STEPS.md](NEXT_STEPS.md). Do not put working features in any of them.

- **MISSING_FEATURES.md** — only capabilities that are not implemented or not fully functional (including LOM blocks).
- **MCP_ISSUES.md** — only faults seen when using the MCP, in enough detail to reproduce. Not a changelog of what works.
- **NEXT_STEPS.md** — remaining work only (same rule: no implemented features). 