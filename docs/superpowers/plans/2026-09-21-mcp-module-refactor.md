# MCP Module Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three monolithic MCP implementation files with focused modules while preserving the complete public and wire-level API.

**Architecture:** A thin entrypoint imports one runtime plus domain modules in each backend. Python uses mixins/tool-registration imports; Max JS uses top-level `include()` files supported by the legacy `[js]` engine.

**Tech Stack:** Python 2/3-compatible Ableton Remote Scripts, Python 3/FastMCP, Max JS ES5, pytest, Node syntax checks.

**Spec:** `docs/superpowers/specs/2026-09-21-mcp-module-refactor-design.md`

## Global Constraints

- Baseline commit is `167016a`; preserve all behavior and public names from it.
- No production Python or JavaScript source may exceed 1,000 lines; target domain modules below 800 lines.
- Do not add runtime dependencies or alter ports, payloads, timeouts, backend semantics, or entrypoints.
- Remote Script remains Python 2 compatible; Max handler remains ES5 compatible.
- User override: implementation workers must receive, verbatim, "By default do not use the full superpowers workflows, just implement the requested feature and keep testing minimal" and there is only one review after the whole refactor.

## Review Focus

- Import identity: direct `MCP_Server/server.py` execution and package import register each tool exactly once.
- Method resolution: Remote Script mixin order leaves every dispatched handler available on `AbletonMCP`.
- Max loading: all `include()` files resolve when installed flat and are listed in AMXD dependencies.
- Surface preservation: MCP tools and both command dispatch sets match the committed baseline exactly.
- Runtime compatibility: no Python 3-only syntax enters Remote Script modules and no modern JavaScript enters Max ES5 files.

---

### Task 1: Capture surface contracts and layout tests

**Files:**
- Create: `tests/test_source_layout.py`
- Create: `tests/test_command_surfaces.py`

**Interfaces:**
- Consumes: baseline tool decorators, Python command comparisons, and Max switch cases.
- Produces: stable expected-name sets and a 1,000-line production-file ceiling.

- [ ] Add tests that parse source text/AST without importing Ableton's `_Framework`, asserting the existing MCP tool names and Remote/Max wire command names remain present after the split.
- [ ] Add a layout test that checks refactored production `.py`/`.js` files are at most 1,000 lines, excluding generated AMXD content and documentation.
- [ ] Run `uv run pytest tests/test_source_layout.py tests/test_command_surfaces.py -q` and confirm the monolith-size assertion fails before extraction while surface snapshots pass.

### Task 2: Split the Python Remote Script

**Files:**
- Modify: `AbletonMCP_Remote_Script/__init__.py`
- Create: `AbletonMCP_Remote_Script/control_surface.py`
- Create: `AbletonMCP_Remote_Script/support.py`
- Create: `AbletonMCP_Remote_Script/mixins/__init__.py`
- Create: focused mixins for session/arrangement, clips/notes, devices/browser, racks/routing, transport/mixer, and warp/detail operations.

**Interfaces:**
- Consumes: `create_instance(c_instance)` and every existing `_process_command` target.
- Produces: `AbletonMCP` imported by `__init__.py`, with the same constructor and handler methods.

- [ ] Move constants and compatibility aliases into `support.py`, importing each dependency in the module where its functions execute.
- [ ] Move command methods into domain mixins without changing method bodies except imports and class indentation.
- [ ] Define `AbletonMCP` from the domain mixins plus `ControlSurface`; retain socket lifecycle and dispatch in `control_surface.py`.
- [ ] Keep `__init__.py` limited to importing `AbletonMCP` and returning it from `create_instance`.
- [ ] Run `uv run python -m compileall -q AbletonMCP_Remote_Script` and the surface/layout tests.

### Task 3: Split the FastMCP server

**Files:**
- Modify: `MCP_Server/server.py`
- Create: `MCP_Server/connection.py`
- Create: `MCP_Server/runtime.py`
- Create: `MCP_Server/tools/__init__.py`
- Create: domain tool modules for session/transport, tracks/scenes, clips/notes, arrangement, devices/browser, mixer/routing, and racks/detail operations.

**Interfaces:**
- Consumes: environment variables `ABLETON_HOST`/`ABLETON_PORT`, `AbletonConnection`, `get_ableton_connection`, and all decorated tool functions.
- Produces: one shared `mcp`, direct `main()`, and exactly the baseline tool set.

- [ ] Move socket transport, mutating-command classification, and connection lifecycle into `connection.py`/`runtime.py` without behavioral changes.
- [ ] Move decorated tools into domain modules that import the shared `mcp`, logger, connection accessor, and typing aliases.
- [ ] Make `tools/__init__.py` import every domain module once for registration; make `server.py` bootstrap package imports safely when run by path.
- [ ] Run `uv run python -m compileall -q MCP_Server`, import `MCP_Server.server`, and run the surface/layout tests.

### Task 4: Split the Max for Live handler

**Files:**
- Modify: `MaxForLive/code/lom-handler.js`
- Create: `MaxForLive/code/lom-core.js` and focused `lom-*.js` domain files.
- Modify: `MaxForLive/build_amxd.py`
- Modify: `tests/test_build_amxd.py`

**Interfaces:**
- Consumes: Max top-level `include(filename)` and the existing `dispatch(cmdType, params)` contract.
- Produces: the same command switch and handler globals after all includes load.

- [ ] Keep queue/message handling and dispatch in `lom-handler.js`; include helper/domain files in deterministic dependency order.
- [ ] Move helpers and handlers by domain without changing ES5 bodies or global names.
- [ ] Generate AMXD dependency entries from all `MaxForLive/code/*.js` files and keep flat installation behavior.
- [ ] Extend build tests to verify every split JS dependency is bundled/copied.
- [ ] Run `node --check` for every JS file, `uv run pytest tests/test_build_amxd.py -q`, and `uv run python MaxForLive/build_amxd.py`.

### Task 5: Documentation and integrated verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `DEVELOPMENT.md`
- Modify: `README.md` only if entrypoint/module references need correction.

**Interfaces:**
- Consumes: final module trees and existing deployment workflow.
- Produces: concise contributor maps that point future work to the right domain module.

- [ ] Document the three module maps and the rule that new commands belong in the matching domain file.
- [ ] Run `uv run pytest -q`, Python compileall, all Max JS syntax checks, `uv run python tools/check_skill_mirrors.py`, and `git diff --check`.
- [ ] Deploy the Remote Script, reload Live only if safe, query `get_session_info`, and run `uv run python tools/_verify_lom_batch_live.py`; report any environment-dependent checks separately.
- [ ] Run one consolidated Luna 5.6 Extra High review over the complete diff, apply only confirmed fixes, and repeat the focused verification once.
