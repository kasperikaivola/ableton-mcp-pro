# MCP Module Refactor Design

## Goal

Split the three oversized implementation files into focused modules without changing MCP tool names, wire commands, argument contracts, return payloads, Live behavior, or supported entrypoints.

## Baseline

- `AbletonMCP_Remote_Script/__init__.py`: 5,180 lines.
- `MCP_Server/server.py`: 2,989 lines.
- `MaxForLive/code/lom-handler.js`: 3,387 lines.
- Commit `167016a` is the clean behavioral baseline.

## Architecture

### Python Remote Script

Keep `AbletonMCP_Remote_Script/__init__.py` as Live's tiny `create_instance` entrypoint. Put the concrete `AbletonMCP` class and socket/dispatch lifecycle in `control_surface.py`; move command implementations into domain mixins under `AbletonMCP_Remote_Script/mixins/`. Mixins may call shared methods on `self`, but no mixin owns socket lifecycle or constructs the control surface.

### MCP server

Keep `MCP_Server/server.py` as the direct executable and exported `mcp` entrypoint. Move connection state and socket transport into `connection.py`, construct the shared FastMCP instance in `runtime.py`, and register decorated tools by importing domain modules under `MCP_Server/tools/`. Direct execution with `python MCP_Server/server.py` and package import as `MCP_Server.server` must both work.

### Max for Live

Keep `MaxForLive/code/lom-handler.js` as the `[js]` bootstrap with queue handling and top-level `dispatch`. Split helpers and domain handlers into ES5 files loaded with Max's supported top-level `include()` mechanism. The AMXD dependency cache and install flow must include every split JS file; installed files remain flat beside the AMXD.

## Boundaries

- Prefer domain files below 800 lines; no production Python/JavaScript source may exceed 1,000 lines after the split.
- Preserve Python 2-compatible Remote Script syntax and ES5 Max JS syntax.
- Preserve every existing MCP tool and wire command, including the feature batch committed in `167016a`.
- Do not redesign behavior, rename public operations, change payloads, or add dependencies.
- Existing provider-neutral skill mirrors and unrelated files remain untouched.

## Validation

- Snapshot and compare MCP tool names and both backend command surfaces before and after extraction.
- Compile every Python module, run Node syntax checks for every Max JS file, run existing tests, build the AMXD, run skill-mirror and diff checks.
- Deploy/reload Live only after static checks pass, then run read-only session verification and the focused reversible LOM smoke harness.
- Perform one consolidated review after all three refactors and documentation are complete.
