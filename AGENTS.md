# Agent workflow

This repository exposes Ableton Live through an MCP server. Keep guidance provider-neutral, preserve concurrent work, and keep changes focused.

## Source layout

- `AbletonMCP_Remote_Script/__init__.py` is the tiny Live entrypoint. `control_surface.py` owns the class, socket, and dispatch; `support.py` contains shared constants/compatibility helpers; `mixins/*.py` contains command-domain implementations.
- `MCP_Server/server.py` is the tiny executable/importable entrypoint. `connection.py` owns TCP policy; `runtime.py` owns the logger, lifespan, and shared `mcp`; `tools/*.py` contains decorated domain tools, registered once by `tools/__init__.py`.
- `MaxForLive/code/lom-handler.js` bootstraps and dispatches. Flat `lom-*.js` files are top-level `include()` modules; `MaxForLive/build_amxd.py` discovers, bundles, and installs all `code/*.js` flat.

## Development

- Add new commands to the matching domain module. Update the Remote Script and Max expectations in `tests/test_command_surfaces.py` only when the public command surface intentionally changes.
- `tests/test_source_layout.py` enforces a 1,000-line ceiling for each production source file.
- Use `uv run` (or the project environment) for Python commands, keep Live-connected checks explicit, and run `python tools/check_skill_mirrors.py` after skill edits.
- Keep `MISSING_FEATURES.md`, `MCP_ISSUES.md`, and `NEXT_STEPS.md` limited to actual missing capabilities, observed faults, and remaining work.
