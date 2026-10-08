# Serum Preset Editing Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one final whole-request review. User instructions waive repeated approvals and per-task reviews.

**Goal:** Agents inspect and edit complete Serum presets without consuming embedded audio in chat.

**Architecture:** Independent codec and bounded query/editor helpers under MCP_Server; thin decorated tools. Files remain authoritative, SHA256 guards prevent stale edits.

**Tech Stack:** Python >=3.10, cbor2, zstandard, existing FastMCP.

**Spec:** ../specs/2026-10-04-serum-presets.md

## Global constraints

- Preserve source files, unknown fields and embedded assets; no live instrument writes.
- 256 MiB input/decoded cap; pages <=100; depth <=5; summary nodes <=400; <=100 operations.
- Preserve concurrent repository changes; each production source <1000 lines.

## Review focus

- Malformed headers/decompressed size mismatches must fail without writing.
- Stale hashes, failed tests and mixed valid/invalid edits must leave outputs absent.
- Escaped pointer keys and indexed arrays must target the correct value.
- Large samples must remain unchanged and absent from ordinary search responses.
- Existing outputs/source aliases and non-JSON CBOR types must not silently lose data.

## Tasks

- [x] Implement codec, atomic output and lossless binary editing; tests for malformed input, limits, source aliases and conversion fidelity.
- [x] Implement bounded pointer reads/search/comparison and guarded patch operations; tests for pagination, arrays, escapes, stale hashes and batch failure.
- [x] Register offline MCP tools, dependencies, guide workflow and public-surface expectations.
- [x] Run focused tests and real fixture structural check, inspect entire diff, complete final review and document remaining Live validation boundary.

## Completion evidence

- Real fixture original/JSON/repackaged decoded state equality verified. Temporary
  decay edit changed only `/data/Env0/plainParams/kParamDecay`; all 281088 samples
  preserved, original bytes untouched. Complete JSON/binary conversion matched.
- Targeted oscillator read ~2340 characters, decay search ~715 characters.
- One final Luna read-only review completed; mapping allocation finding fixed
  using islice. Array scalar classification deliberately checks all values locally
  to avoid incorrectly hiding nested controls based on an approximate sample.
- Focused codec/query/edit, guides, public surfaces and source-size checks pass;
  mirrored skills match. No live Serum loading or audio verification performed.
