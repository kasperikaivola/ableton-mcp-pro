# Audio Asset Search Implementation Plan

> **For agentic workers:** Execute inline using superpowers:executing-plans. Spec/plan auto-accepted under user instructions; one final review, minimal testing.

**Goal:** Find presets/audio assets without walking Ableton browser folders manually.

**Architecture:** Read-only filesystem search tool with segment-aware wildcard matcher, bounded traversal and paginated paths; guide/skill discovery instructions.

**Tech Stack:** Python stdlib and FastMCP.

**Spec:** ../specs/2026-10-04-audio-asset-search.md

## Global constraints

- Default root G:/AudioAssets; no writes or symlink/junction traversal.
- Limit 1..100 results, scan budget 1..1000000 entries, <=10 seconds traversal.
- Preserve current dirty changes; no Live dependency or browser URI invention.

## Review focus

- Nested case-insensitive matches and ** zero-directory matches.
- Pagination must continue after the last actually returned match.
- Scan/time limits must explicitly report incomplete results.
- Permission errors/symlinks must not silently imply complete library coverage.
- Legacy FXP results must not imply Serum 2 editor compatibility.

## Implementation

- [x] Add matcher/search, MCP registration and focused temporary-library tests.
- [x] Update preset discovery docs, AGENTS and mirrored synth skill.
- [x] Run focused checks, a read-only G:/AudioAssets search and final diff review.

## Evidence

9 focused checks passed, 1 symlink creation check skipped because this Windows
process lacks permission. All 21 skill mirrors match; diff whitespace check clean.
Read-only full Init search examined 52151 entries and found G:/AudioAssets/Init.SerumPreset.
Preset and legacy FXP queries returned paginated real paths from nested folders.
Final Luna read-only review found no material issue. No asset writes or Live changes.
