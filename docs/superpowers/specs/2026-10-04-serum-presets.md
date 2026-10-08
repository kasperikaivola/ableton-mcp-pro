# Serum preset file editing

Implement offline Serum 2 preset inspection, targeted reads/search, edits, conversion
and comparison. User-approved scope: integrate the format understood by the local
serum-preset-packager, keeping large embedded assets out of agent context.

Use an independently implemented XferJson container codec: uint64 metadata length,
JSON metadata, uint32 decoded CBOR length, uint32 encoding 2, Zstandard CBOR.
Preserve all decoded values, unknown fields and embedded assets in binary edits.
JSON export must fail explicitly on non-JSON CBOR types rather than lose them.
Reject unsupported containers, invalid headers and oversized decompression.

Expose six offline MCP tools: info, read, search, edit, convert and compare.
JSON Pointer addresses metadata and data, including array indices. Reads/search
are paginated and bounded; large scalar arrays are summarized and search skips
their values by default. Explicit array reads can retrieve a small slice.
Search returns actual paths and values without guessed synth semantics.
Edits accept add/replace/remove/test operations, require an expected source SHA256,
validate the whole operation batch before writing, default to dry-run and require
a separate output file. Existing outputs need explicit overwrite. Publish through
a temporary file, preserving the source. Comparison reports bounded changed paths.

Support binary presets and packager-compatible JSON. Limit input/decoded payload
to 256 MiB, response pages to 100 entries, reads to depth 5 and 400 summary nodes,
edits to 100 operations. No Live connection, invented enum mappings, default
values, automatic patch loading or claims of vendor-defined parameter validity.

Evidence: fixture original equals JSON equals user repackaged preset; metadata
Serum2 2.0.14; stereo embedded_audio has 140544 values per channel. Do not add
copyrighted preset fixtures to this repo. Format research attribution is in docs;
no upstream source is copied (the clone has no license file).

Validation: focused synthetic codec/editor tests, public tool/source-layout tests,
one real-fixture edit/repack structural comparison with original untouched. Actual
Serum loading and audible results remain unverified.
