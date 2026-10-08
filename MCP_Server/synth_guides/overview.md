# Hybrid synth sound design for Ableton agents

Original operating guide for Serum 2 and Omnisphere. Read `workflow`, then the
chosen synth's `identity` and relevant sections; use `all` for a complete guide.
These references describe design controls, not this instance's current state.

For preset/asset discovery, use `search_audio_assets` under `G:/AudioAssets`.
Filename wildcards search all nested folders; folder patterns support `**`.
Use returned paths and coverage/pagination flags rather than invent filenames.

For complete offline Serum preset reads/edits, retrieve
`get_synth_sound_design_guide(synth="serum-presets", section="workflow")` and
`tools-and-paths` / `editing-semantics`. File editing preserves hidden state but
does not apply it to the loaded instance. See [preset workflow](serum-presets.md).

## Workflow

### Interpret the request

“Add a mystical FX synth to make this track fuller” means inspect the song,
choose one of the user's installed synths, create a complementary MIDI track,
load its instrument and provide a reproducible patch design in chat. “Track X
sounds bland, suggest changes” means inspect and propose changes; do not write
parameters, initialize, replace its preset, or duplicate tracks unless requested.
An explicit “improve/change this patch” permits targeted edits plus manual steps.
For Serum preset transformations such as “make this synth preset faster/darker/
bouncy”, automatically use `serum-presets/existing-preset-edits`: identify the
existing file/current export, unpack complete JSON to disk, edit separate JSON,
repack a separate `.SerumPreset` and verify decoded changes. Deliver the edited
file; preserve the original and unrelated patch state. This is an apply request,
not a suggestion request. File export/edit/load status remains explicit.

“Create a Serum 2 preset in this style” means design and write a separate
`.SerumPreset` using the offline tools, not just give a recipe or change a few
configured knobs. Read `serum-presets/workflow`, `new-preset-design` and
`module-editing`. Deliberately design sources, sub/noise, filters/routing,
envelopes/LFOs, modulation/performance, ordered FX and voicing. Use compatible
reference state for hidden controls; missing Configure parameters do not block
offline edits. A file-only request needs no Live connection or new track. For a
requested playable addition, generate the preset as well as creating the track,
then load through a verified mechanism or hand off loading explicitly.

Do not require another approval for creation already requested. Ask only when
identity is ambiguous, the target is unavailable, or an essential choice cannot
be inferred. Read-only work can continue while awaiting that answer.

### Read context before choosing a sound

1. `get_session_info`: tempo, meter, track names, broad instrumentation.
2. `get_track_info` on the target and relevant neighbors: device identity,
   instrument/effect order, clips, routing and mixer state. Use rack-chain reads
   where the instrument is nested. If the tools cannot address the nested device,
   preserve its identity and design manually; do not treat the enclosing rack as
   the synth. Recheck indices after insertion/duplication.
3. `get_arrangement_info` / `get_arrangement_clips` for the relevant section;
   inspect notes with `get_arrangement_clip_notes` or `get_clip_notes` if needed.
   Describe inferred role/key/register with confidence. Audio-only material may
   leave harmony unknown. Track labels are clues, not proof of tone or key.
4. For an existing synth, read unfiltered `get_device_parameters` (omit query).
   Host names may be requested as an inventory aid; they are not writable knobs.
   Record actual normalized values, display values and parameter indices.
5. Retrieve `get_synth_sound_design_guide(synth="serum2"|"omnisphere", section="all")`
   or its index plus relevant sections. Establish plug-in version and starting
   preset when available. A name without a version does not establish a build.

Do not claim to have listened without an actual audio observation. Say “based on
track names, MIDI and configured controls” when that is the available evidence.
Live parameter reads do not expose a complete plug-in GUI or unsaved preset state.
The offline Serum preset tools do expose exported file state, including hidden
controls; use them for new Serum designs and keep file evidence separate.

### Choose a synth for the role

| Need | Useful first choice | Reason / constraint |
|---|---|---|
| Precise animated timbre, digital FX, clean modulation | Serum 2 | Explicit oscillator/warp/matrix design; verify assets and mappings |
| Organic, cinematic, acoustic/choir texture or hybrid atmosphere | Omnisphere | Soundsource layers and synthesis modifiers; selected library name needs confirmation |
| Existing patch improvement | Its current synth | Keep musical identity; avoid swapping the instrument |
| Uncertain library/version or no available plug-in | Explain the missing item | Offer a supported alternate design; do not silently substitute |

Choose the smallest addition that fills a real gap. A fuller mix can need a quiet
midrange texture, transient detail or movement rather than another bass/pad.
State role, register, rhythmic density, width and how it avoids existing parts.

### New track procedure

1. Find a loadable Serum 2/Omnisphere browser item or a user-confirmed rack/preset
   using `get_browser_tree` and `get_browser_items_at_path`. Follow returned paths
   and URIs, including Places/user folders as appropriate. Do not fabricate a
   plug-in URI or assume `insert_device` accepts VST names; it is for native Live
   devices. Browser loading requires a backend that actually exposes it; the
   Max backend has a documented browser limitation. If blocked, provide manual
   loading steps and accurately report what was created.
2. `create_midi_track(index=-1)`, reread the session to identify the new track,
   and name it for the role, e.g. `FX — Mystic Halo`. Avoid changing global tempo,
   playback, existing clip contents or unrelated routing.
3. `load_instrument_or_effect(track_index, uri)`; `get_track_info` to verify the
   resulting instrument, not just an accepted browser-load message. If loading
   fails, stop dependent writes; keep and report the new empty track for recovery.
4. Read the new instance's unfiltered parameter inventory. Establish its actual
   baseline; do not assume a new instance loads Init rather than a saved default.
   If initialization is needed, include it as the first manual step unless a
   reliable supported preset operation was verified.
5. Design the complete target patch using the checklist. Apply only settings
   with a verified mapping and a defensible normalized value. Recheck display
   values after writes. Log skipped/failed settings in the final handoff.
   For Serum 2, implement the full design in a separate preset with the offline
   workflow rather than restricting it to Configure knobs. Load that output
   before any live adjustments that loading would otherwise replace; verify
   live state separately. If loading is unavailable, still deliver the file.
6. Add an audition clip only when useful to the requested playable addition;
   infer musical material from reliable notes or give a pitch-neutral FX idea.
   Keep it on the new track and avoid launching it without a reason to change
   transport. Never describe a track with pending manual settings as finished.

The tool returns recommendations; it does not execute this sequence itself.

### Existing track procedure

For requested Serum preset edits, use the JSON round trip above. Identify or
obtain an export of the current patch; do not substitute an old library file for
unsaved instance state. Implement the targeted transformation in that JSON and
deliver the repacked preset, then load/verify separately. Missing Configure
controls do not block file edits. The full new-preset redesign checklist is not
a requirement to alter unrelated categories in an existing patch.

Keep the current preset/source and automation. For suggestions alone, take a
read-only snapshot and give one recommended improvement plus up to two options.
For requested edits, record the before values, make a small coherent change,
read back, and preserve everything outside that change. Do not initialize an
existing patch to fit a recipe. Unmapped settings remain unknown unless the user
confirms them or supplies an appropriate screenshot/name.

Tie each idea to the complaint: more timbral movement, clearer attack, stronger
body, a contrasting layer, or expressive control. Identify what evidence led to
the suggestion and what is a hypothesis. Give a reversible A/B plan with matched
level; do not certify the audible result from a successful parameter write.

## Values

MIDI CC, host automation and Live's Configure parameters are distinct mechanisms.
A synth may offer MIDI Learn or host automation for many controls while this
MCP can only write its configured Live parameter surface. MIDI Learn, opening
Configure and establishing mappings can still require manual work.

| Evidence/status | Meaning |
|---|---|
| Observed | Read from the current target or supplied by the user; name the source |
| Inferred | A reasoned hypothesis from musical context, never a current-control claim |
| Proposed | A design target; not proof the library asset exists or setting is applied |
| MCP-verified | Write succeeded and actual readback supports the intended setting |
| Encoded in output; not loaded | Decoded file comparison verifies preset state; live application still requires loading/checking |
| User-confirmed | User reports applying/seeing it; not an MCP readback |
| unknown/unverified | Missing version, label, mapping, asset, or current value |
| not applied — set manually | Every intended setting not implemented by the MCP |

Use Hz, ms/s, dB, cents, semitones, voices, %, degrees and note divisions in the
recipe. Define what each % means: UI knob percentage, wet mix, sample duration,
or modulation span. Never convert 1200 Hz into 0.12, or assume the physical range
is linear. Discrete selections need verified labels/value items; opaque enum
indices are insufficient. If the tool gives only a normalized value without a
calibrated display mapping, hand off the intended physical value manually.

Modulation instructions need source, exact destination, base value, end points,
depth/polarity, waveform, rate, sync mode, phase and retrigger/loop behavior.
“Add movement” and “turn Macro 1 to 50%” are incomplete unless its routes are known.
For inaccessible automation, give its explicit time/value curve and state that
the curve has not been implemented. A fixed value is not an automation substitute.

## Checklist

Use this to make a **new** patch reproducible. Existing improvements need a complete
change recipe and stated prerequisites, not an invented reconstruction of the
unseen original. Unchanged controls can explicitly say “retain current setting”.

- Identity: track name/index, device index or rack chain, role, synth/version,
  baseline preset/Init state; Omnisphere Part/Layer/MIDI channel/output.
- Sources: all active oscillator/layer modes; exact verified table/wave/sample
  name or user path; source position/loop; pitches, levels, pan, phase/randomness,
  unison voices/detune/spread; inactive modules explicitly off or retained.
- Synthesis: warp/FM/ring/sync/shaper/granular/spectral settings and prerequisites;
  oscillator/sub/noise and filter/FX routing, direct bypass/send amounts.
- Filters: each enable/type, cutoff/resonance/drive/mix/variant, tracking and routing.
- Amplitude: ADSR/hold/delay as applicable, curves, velocity response, polyphony,
  mono/legato/glide, bend range, tuning and retrigger.
- Modulation: every intended source/destination route and all timing/depth details;
  state unused routes absent on an Init-based recipe.
- FX: exact bus/rack/slot, order, enable/bypass, type/algorithm, every intended
  control, wet/dry vs send topology, tempo-sync state/division and compensation.
  For controls not deliberately changed, specify the exact baseline preset.
- Performance: wheel/velocity/aftertouch/macros/MPE routes; arp/sequencer/Orb state;
  external MIDI/automation prerequisites. Keep inaccessible ones manual.
- Context: pitch/register and duration, harmonic uncertainty, expected function,
  level matching and suggested audition; do not confuse synthesis with mixing.
- Delivery: ordered manual handoff, verified MCP changes separately, unknowns,
  save-as name and asset dependencies. No unfinished step is silently omitted.

## Handoff

Put the design in the final chat, not only in a file. Lead with role and rationale,
then summarize observed context and assumptions. Give the reproducible patch or
the targeted improvement recipe, followed by verified writes and the full manual
table. Group settings into ordered steps so initialization cannot erase earlier
manual work. Include this block for each designed or edited instance:

```text
Serum 2 — manual settings
Track: <name> (index <n>), device <n>, role: <role>
Section / control | Desired value or selection (units) | Status
<location and routing> | <exact intended value> | not applied — set manually
```

```text
Omnisphere — manual settings
Track: <name> (index <n>), device <n>, role: <role>
Version: <verified version or unknown/unverified>; Part <n>; Layer <A/B/C/D>
Section / control | Desired value or selection (units) | Status
<Part/Layer/rack and control> | <exact intended value> | not applied — set manually
```

If every intended change was actually verified, write `No manual settings required
for the verified changes.` Access uncertainty is not evidence that there are no
gaps. Suggestions without writes remain proposals/manual steps. Unknown asset
choices must be marked `proposed choice — availability unknown/unverified` and
confirmed before dependent work. User-confirmed settings stay separate from
MCP-verified writes.

For offline Serum output, group decoded-verified settings as `encoded in output;
not loaded` and give a loading/verification step; do not ask for manual recreation
of settings already encoded. True unencoded gaps still need the exact manual
table. File-only requests identify source/output instead of a live track/device.

## Extension

To support another synth, add an original version-scoped reference with the same
identity/control/recipe/handoff contract and an entry in the retrieval tool's
allowlist. Add its selection rationale to this guide and the skill. Do not infer
compatibility simply because the plug-in exposes similarly named parameters.

## Sources

Control facts are grounded in the selected synth's vendor references, cited in
its `sources` section. Workflows, recipes and improvement suggestions are original
design proposals. Installed versions, factory libraries, Configure mappings and
audible outcomes must be verified in the user's session.
