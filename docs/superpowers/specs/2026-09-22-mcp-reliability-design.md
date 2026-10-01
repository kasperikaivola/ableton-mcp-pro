# MCP Reliability Design

## Goal

Make long-lived Ableton MCP processes reliable for repeated reads and edits, bound AI-generation calls, report browser loads truthfully, preserve direct script startup, and expose individual Drum Rack sample loading where Live's public API supports it.

## Design

- Serialize each process's request/response exchange on its persistent TCP socket.
- Marshal ordinary Remote Script command dispatch onto Live's main thread. Keep the existing long-running recording commands on worker threads because they already marshal their individual Live operations.
- Keep direct `python MCP_Server/server.py` startup supported and regression-tested.
- Run MidigenAI through a child process with a configurable timeout so a model stall can be terminated and returned as an MCP error.
- Report the browser item and track accepted by Live after a load. Do not claim an immediate device inventory when Live updates it asynchronously.
- Add `load_drum_pad_sample` for Live 12.4+: insert a Drum Rack chain, set its input note, insert Simpler, and call `replace_sample`. Reject unsupported Live versions before mutating the rack.

## Error handling and compatibility

Timeouts close the affected TCP socket before the next request reconnects. Drum-pad loading validates track, rack, note, file path, and Live capability. Existing tools and response formats remain unchanged except for the misleading successful device-load text.

## Verification

Use focused tests for direct import, socket serialization/reconnect behavior, main-thread dispatch source contract, MidigenAI timeout/forwarding, truthful browser-load text, and command-surface registration. Run the existing command-surface and source-layout checks plus syntax checks.
