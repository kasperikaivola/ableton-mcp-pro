# Serum 2 preset creation guidance

New Serum preset requests should produce a separate, substantially designed
`.SerumPreset` using the existing offline tools, rather than just a recipe or a
small Configure edit. Missing Live controls do not block offline creation.
Suggestion-only requests remain read-only; existing-patch edits stay targeted.

The guide must cover oscillator/source selection, sub/noise, both filters and
routing, multiple envelopes/LFOs and curves, modulation and performance routes,
ordered/repeated FX across racks, and voicing. Each category needs a deliberate
edit, a named retained baseline, an off/unused decision, or a specific blocker.
Require musically relevant changes across the categories that define the style,
not arbitrary edit counts or enabling every module.

Use checked local fixtures as version-scoped structural examples, preserving
unknown state and asset descriptors. Do not infer GUI units, source enums or FX
destination addressing from field names. Guard source SHA256, dry-run, write a
separate output and compare decoded state. Distinguish written preset state from
loaded/auditioned state; preserve the final manual-settings handoff.

Surface the creation contract in MCP guide/tool descriptions, overview and Serum
references, mirrored skill, repository agent guidance and README. No new codec,
loading mechanism or tool interface is needed. Preserve existing workspace work.

Validation: existing offline guide/preset tests, skill mirror check and one final
review of the complete instruction change. No live sound claims.

## Existing-preset transformation follow-up

Imperative requests such as faster/darker/bouncy authorize targeted edits of the
identified existing preset. Default to complete JSON extraction, edits to a
separate JSON, and repackaging a separate preset with per-input SHA256 guards.
Preserve patch identity, original files and unrelated state. Validate intended
decoded changes and edited-JSON/output equality. Missing current live exports
require source clarification; opaque non-JSON CBOR uses the disclosed binary
fallback. Suggestions remain read-only; loading/auditioning stays separate.
