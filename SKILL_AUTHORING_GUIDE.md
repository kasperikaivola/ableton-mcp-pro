# Skill Authoring Guide

Best practices for creating and maintaining music production skills for Ableton MCP-capable agents.

Claude discovers skills under `.claude/skills/`; Codex discovers `.agents/skills/`. These are provider-specific discovery paths for the same skills and must remain exact mirrors. After changing a skill, run `python tools/check_skill_mirrors.py`.

## What Makes a Good Skill

### The Bar: "Excellent"
An excellent skill lets an MCP-capable agent execute a complete production workflow — from empty Ableton session to a playable result — using only MCP tool calls.

### Quality Checklist
- [ ] Specific parameter values (not "add some reverb" — "Reverb: decay 3.5s, pre-delay 20ms, diffusion 80%")
- [ ] Actionable via MCP (no manual drag-and-drop, no GUI-only operations)
- [ ] For explicitly hybrid VST workflows, separate verified MCP writes from exact manual UI instructions; follow [synth-sound-design](.agents/skills/synth-sound-design/SKILL.md) and AGENTS.md's handoff contract. This is an intentional exception to the all-MCP checklist item.
- [ ] Build order at the end (numbered steps matching MCP tool sequence)
- [ ] At least one ASCII pattern diagram for drum/rhythm skills
- [ ] Grounded in research (multiple sources including blog posts and videos, not just AI knowledge)
- [ ] Synthesized from 2+ sources
- [ ] 80-140 lines (shorter = incomplete, longer = bloated)

## File Structure

```
.claude/skills/<skill-name>/SKILL.md
.agents/skills/<skill-name>/SKILL.md
```

### YAML Frontmatter (required)
```yaml
---
name: skill-name
description: One sentence. Start with "Create..." Use when the user asks for X, Y, Z, or W.
---
```

The description field controls when a provider activates the skill. Keep the matching files byte-for-byte identical across `.claude/skills/` and `.agents/skills/`; the mirror checker enforces this. Include:
- The primary thing it creates
- 4-6 trigger phrases covering common ways users might ask for it
- No artist names unless truly genre-defining

### Standard Sections

1. **Quick Reference** — Tempo, key, time signature, feel (2-4 bullets)
2. **Sound Design** — Specific synth patches with parameter values
3. **Patterns** — ASCII diagrams, MIDI note values, velocity ranges
4. **Processing** — Effects chain with specific settings
5. **Mixing** — Levels, sidechain, EQ, mono/stereo
6. **Build Order** — Numbered steps matching the workflow

Not every skill needs all sections. A bass skill doesn't need pattern diagrams. A drums skill doesn't need sound design depth. Match the structure to the content.

## MCP and Provider Compatibility

### Always check: can the MCP client actually do this?

**Fully supported operations:**
- Create MIDI tracks, clips, add notes
- Load Operator, Wavetable, Analog, Simpler, Drum Rack
- Load any effect (EQ8, Compressor, Reverb, Saturator, Auto Filter, etc.)
- Load MIDI effects (Chord, Scale, Arpeggiator) via `get_browser_items_at_path("midi_effects")` then `load_instrument_or_effect` (Live already inserts MIDI FX before the instrument). Use `move_device` only to reorder MIDI effects among themselves — Live will not place an instrument in front of a MIDI effect (Remote Script)
- Set device parameters by index or name (normalized 0.0-1.0). For VSTs, only Configure-panel knobs exist; `get_device_parameters` includes inferred groups (e.g. Oscillator A, Filter 1)
- Set track volume, panning, send levels
- Write clip automation envelopes on **session** clips (`set_clip_envelope`). Arrangement clip envelopes are not in the public LOM (track-level automation is GUI-only)
- Apply an existing Groove Pool entry (`get_groove_pool` / `apply_groove`)
- List rack chains; `insert_rack_chain` on Live 12.3+
- Set tempo, time signature

**NOT supported (avoid in skills or note as manual steps):**
- Mapping a new parameter onto a rack macro (Map mode is GUI-only; existing macros can be set)
- Slicing audio to MIDI
- Freezing/flattening tracks
- `insert_rack_chain` on Live versions before 12.3 (load a multi-chain rack from the browser instead)

**Supported mixdown path:** `resample_master` records the main mix through a resampling track. Live has no general export command.

For fully automated skills, find a supported workaround for required unsupported operations. For explicitly requested hybrid sound design, keep the manual steps actionable and visible in chat; do not claim the full design was executed by MCP.

## Writing Parameter Values

### Be specific enough for `set_device_parameter`
MCP sets parameters by index and normalized value (0.0-1.0). Write values that translate:

**Good:** "Filter cutoff: 45% (low-pass 24dB)"
**Bad:** "Open the filter a bit"

**Good:** "Attack: 5ms, Decay: 200ms, Sustain: 70%, Release: 50ms"
**Bad:** "Short punchy envelope"

### Operator parameters to know
- Oscillator waveform is set via device parameter (not always obvious which index)
- FM amount = modulator oscillator's level
- Algorithm/routing = a single parameter with discrete values
- Always specify: waveform, level (dB), coarse tune, fine tune for each active oscillator

### When exact values aren't possible
Some settings depend on context (e.g., "sidechain release depends on tempo"). Give a formula or range:
- "Release: ~120ms at 140 BPM (one 16th note = 107ms, leave headroom)"
- "Cutoff: 30-50% depending on how bright you want the attack"

## Pattern Diagrams

### ASCII Format
```
Beat:  1 . . . 2 . . . 3 . . . 4 . . . | 1 . . . 2 . . . 3 . . . 4 . . .
Kick:  X . . . X . . . X . . . X . . . | X . . . X . . . X . . . X . . .
Snare: . . . . X . . . . . . . X . . . | . . . . X . . . . . . . X . . .
Hat:   X . X . X . X . X . X . X . X . | X . X . X . X . X . X . X . X .
Ghost: . . . g . . . . . g . . . g . . | . g . . . . . g . . . g . . g .
```

- Use `X` for main hits, `g` for ghost notes
- 16th note resolution (4 positions per beat)
- 2 bars separated by `|`
- Include velocity guidance in text ("Ghost: velocity 40-60, main hits: 100-127")

### When to include patterns
- Drum skills: always (2-3 patterns minimum)
- Bass skills: include if the rhythm is important (e.g., trance bass types, walking bass)
- Chord/pad skills: usually not needed

## Research Process

### Minimum: 2 distinct sources per skill

Use a mix of video tutorials and blog posts to ground each skill in real production knowledge:

- Search for specific techniques, not generic overviews
- Look for concrete parameter values and workflow steps
- Different creators have different approaches — that's the point
- Synthesize insights across sources rather than copying from any single one

### What to extract from sources
- Specific parameter values (filter cutoff at X Hz, decay at Y ms)
- Sound selection tips (why this waveform, why this sample type)
- Pattern placement insights (why the kick goes HERE, not there)
- Processing order and reasoning

### What NOT to copy
- Direct quotes from tutorials
- Artist name attributions (unless truly genre-defining)
- Exact phrases that would identify the source
- Subjective opinions presented as rules

## Maintenance

### When to update a skill
- New MCP capabilities unlock previously-blocked features
- A technique turns out to be wrong in practice (test against Ableton)
- A user reports that a skill produces bad results
- New research reveals better approaches

### When to remove a skill
- Core workflow depends on MCP features we don't have
- Overlaps too heavily with another skill
- The genre/technique is too niche to be useful
- Can't produce a usable result even with workarounds
