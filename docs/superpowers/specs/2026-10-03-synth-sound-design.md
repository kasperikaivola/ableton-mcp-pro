# Synth sound-design reference design

The user wants agents to turn requests such as “add a mystical FX synth” into a
context-aware new Serum 2 or Omnisphere track and a detailed patch recipe, and
to propose improvements to an existing patch despite incomplete plug-in access.

## Architecture and scope

Add original, agent-oriented Markdown references in `MCP_Server/synth_guides/`.
Expose them with a read-only MCP tool, `get_synth_sound_design_guide`, so clients
outside this checkout can use the same guidance. Package the references with the
server. Add a provider-mirrored `synth-sound-design` skill and link the workflow
from AGENTS.md, CLAUDE.md and README.md. Plug-in inventory responses should point
agents to the guide; use existing Live tools for creation/loading/writes.

The alternatives are repository-only documentation (inaccessible to remote MCP
clients) or a patch executor (cannot implement GUI-only controls reliably).
The reference tool plus existing controls meets the requested scope.

## Content contract

- Cover Serum 2 oscillator modes, source selection/editing, dual warp/routing,
  filters, modulation, FX buses/types/controls, arpeggiator/clips, performance,
  global settings, asset dependencies and saving.
- Cover Omnisphere version/Part/Layer identity, browsing, Sample/Synth modes,
  synthesis modifiers, granular/unison/Harmonia, filters, envelopes/LFO/matrix,
  FX racks/types/controls, Orb, arpeggiator, multitimbral routing, saving and
  version-gated additions. Current-version documentation access limits must be
  explicit; legacy documentation is not proof of modern labels/ranges.
- Include new-track and suggestion-only existing-track workflows, patch
  completeness checklist, concrete recipes and conditional improvement ideas.
- Separate observed, inferred, proposed, user-confirmed and MCP-verified facts.
  Names and MIDI notes are context, not evidence of what a patch sounds like.
- Read the target instance's unfiltered parameter inventory before writes.
  No assumed physical-to-normalized conversion, opaque FX mappings, preset
  names, wavetable indices or installed library contents.
- Every design/edit gets a final-chat `<Synth> — manual settings` block listing
  all intended unapplied values, units, locations and routing. Retain the
  existing Serum contract; extend it to Omnisphere with Part/Layer identity.
- New sound requests allow creation/loading, but suggestion requests alone do
  not allow editing the existing patch. Preserve its settings and automation.
- References must be available offline, without Live or web access. No new
  production dependency, Live command or Remote Script deployment is needed.

## API

`get_synth_sound_design_guide(ctx, synth="overview", section="index") -> str`
returns JSON. Synth identifiers: overview, serum2, omnisphere (friendly aliases
accepted). Index returns section titles and tool instructions. A section returns
its Markdown; `all` returns the complete selected reference. Unknown input returns
an actionable JSON error and available choices. Resolve only allowlisted package
files. No caller-controlled paths and no Live connection.

## Validation

Focused tests cover tool registration, all reference sections, invalid inputs,
offline use and plug-in reminders. Check skill mirrors, production source size,
diff formatting and wheel contents. One whole-request review after implementation;
no per-task review loop or project mutation in Live during development.

Spec auto-accepted under the supplied AGENTS instructions. Implementation is
inline in the clean existing feature checkout; no unsolicited commits or pushes.
