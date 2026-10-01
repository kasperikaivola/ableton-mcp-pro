# MCP Reliability Implementation Plan

> **For agentic workers:** Execute natively in this session; keep testing focused and perform one final whole-change review.

**Goal:** Remove the observed MCP stalls and misleading responses while adding supported individual Drum Rack sample loading.

**Architecture:** Protect the client socket transaction, enforce Live main-thread affinity at the Remote Script boundary, isolate AI generation in a timeout-controlled child process, and implement pad loading from documented Live 12.4 LOM primitives.

**Tech Stack:** Python, Ableton Remote Script/LOM, FastMCP, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-mcp-reliability-design.md`

## Global Constraints

- Preserve existing uncommitted MidigenAI and documentation work.
- Keep public behavior provider-neutral and avoid unrelated refactors.
- Use only focused regression tests and one final review.

## Review Focus

- Concurrent tool calls sharing one TCP connection must not interleave requests or responses.
- All ordinary Live object reads and writes must execute on Live's main thread.
- A timed-out AI generation must return promptly and terminate its child process.
- Browser-load success must not imply an observed device list.
- Drum-pad loading must not mutate the rack on unsupported Live versions.

### Task 1: Connection and Remote Script dispatch reliability

**Files:** `MCP_Server/connection.py`, `AbletonMCP_Remote_Script/control_surface.py`, focused tests.

- [ ] Add failing tests/source assertions for serialized exchanges and main-thread dispatch.
- [ ] Add a per-connection lock and close sockets cleanly on communication failures.
- [ ] marshal ordinary command processing through a bounded main-thread helper.
- [ ] Run focused tests.

### Task 2: Bounded MidigenAI and truthful load responses

**Files:** `MCP_Server/tools/midigenai.py`, `tools/midigenai_bridge.py`, `MCP_Server/tools/devices_browser.py`, focused tests.

- [ ] Add failing timeout and response tests.
- [ ] Execute generation in a timeout-controlled subprocess.
- [ ] Return the accepted browser item/track without an invented device inventory.
- [ ] Run focused tests.

### Task 3: Drum Rack pad sample loading

**Files:** MCP tool, Remote Script mixin/dispatch, Max command module/dispatch where practical, docs, command-surface test.

- [ ] Add the expected public command and focused validation tests.
- [ ] Implement Live 12.4+ chain/Simpler/sample setup with preflight capability checks.
- [ ] Update capability documentation.
- [ ] Run command-surface and syntax checks.

### Task 4: Final verification and review

- [ ] Run focused tests, source-layout tests, Python compile checks, JavaScript syntax checks, and `git diff --check`.
- [ ] Review the whole diff once for correctness, scope, and preservation of concurrent work.
