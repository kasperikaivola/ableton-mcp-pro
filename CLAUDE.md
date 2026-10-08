# Ableton MCP Pro

This file is the Claude adapter for the project, not the canonical workflow contract. Use [AGENTS.md](AGENTS.md) for provider-neutral guidance; Claude discovers `.claude/skills/`, while Codex and other MCP-capable agents discover the exact mirror in `.agents/skills/`.

Control Ableton Live through MCP tools. This project has two parts:

1. **Remote Script** (`AbletonMCP_Remote_Script/__init__.py`) — runs inside Ableton, listens on TCP port 9877
2. **MCP Server** (`MCP_Server/server.py`) — exposes 50+ tools to AI assistants via FastMCP

## Key Conventions

- **Track indexing**: 0+ for regular tracks, `-1` for master, `-2`/`-3` for return A/B
- **Live parameter writes**: Normalized 0.0–1.0; offline Serum preset values use their native file representation, not this normalization
- **Clip positions**: In beats (4.0 = 1 bar at 4/4)
- **MIDI notes**: pitch 0–127 (C3=48, C4=60), velocity 0–127
- **Arrangement editing** — direct audio/MIDI clip insertion is supported; use record_arrangement for session-based recording and keep LOM limits in mind
- **Serum 2 handoff** — follow AGENTS.md's mandatory `Serum 2 — manual settings` final-chat section for every patch design/edit; enumerate intended wavetable, FX, modulation, and other settings not applied through MCP, with explicit desired values and manual status.

## Music Production Skills

Claude discovers 21 skills in .claude/skills/; .agents/skills/ is the byte-for-byte mirror for other MCP-capable agents.

For Serum 2/Omnisphere patch creation or improvement ideas, use
[synth-sound-design](.claude/skills/synth-sound-design/SKILL.md) and
`get_synth_sound_design_guide`. Follow AGENTS.md's context inspection,
suggestion-only behavior and both synths' mandatory final-chat manual handoffs.
For new Serum presets, actually write a separate `.SerumPreset` via the offline
tools and the `serum-presets` guide's `new-preset-design` / `module-editing`
sections. Implement substantial style-defining source, filter, envelope,
modulation, FX and voicing changes; missing Configure controls do not block file
creation. File-only requests need no Live connection. Verify decoded edits and
report loading/auditioning separately.
For existing Serum transformations (“make this preset faster/darker/bouncy”),
automatically follow `serum-presets/existing-preset-edits`: unpack the existing
file/current export to complete JSON, edit separate JSON, repack a separate preset
and compare decoded state. Preserve the original and unrelated patch settings.

See [SKILL_AUTHORING_GUIDE.md](SKILL_AUTHORING_GUIDE.md) for creating new skills.

## Development

- See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture, threading model, adding commands, and known issues
- See [NEXT_STEPS.md](NEXT_STEPS.md) for roadmap and MCP capability gaps
