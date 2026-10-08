# Complete Serum preset subtree copies

Spec (auto-accepted): generic decoded-state edits already work for all addressable
fields. Add the missing ability to reuse complete state without transferring a
bounded preview or huge asset through chat. Extend `edit_serum_preset` with JSON
Patch `copy`: `from` and `path`, optionally `source_file_path` plus mandatory
`source_sha256` for a reference preset/JSON. Preserve opaque types, source files
and unrelated state; guard donor hashes before publication. Copy into arrays
inserts, objects sets/replaces; parents must exist. Do not invent mappings or
automatically remap FX/matrix addresses.

Implementation plan:
- [x] Extend the tree patcher and offline tool with guarded complete copies.
- [x] Document FX/matrix/WT/curves and other module recipes in a retrievable guide;
  route the mirrored skill and MCP instructions to it.
- [x] Focused checks: opaque/large asset fidelity, stale donor and no-output
  failure, JSON edit/repack multi-module fidelity; existing guide/surface checks.
- [x] Final self-review of the complete change and honest live-verification limits.

Results: 38 focused preset, guide, command-surface and source-layout tests passed;
21 skill mirrors matched. The new guide section retrieved successfully. Final
self-review confirmed copies use complete disk state, preserve opaque CBOR on the
binary path, recheck donor hashes after encoding and leave mapping/remapping
decisions explicit. Existing tool signatures and the public command set remain
unchanged. Running MCP clients need a server/connection reload to use new copy
semantics. No live synth patch was changed for this implementation.
