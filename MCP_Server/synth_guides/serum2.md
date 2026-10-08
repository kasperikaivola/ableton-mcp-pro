# Serum 2 control reference for agents

For full offline preset state (including embedded assets and hidden controls),
read [preset file workflow](serum-presets.md), available through
`get_synth_sound_design_guide(synth="serum-presets", section="workflow")`.
Generated files still require loading and verification in the target instance.

For a requested new preset, **actually create the file** with substantial
style-defining edits, including hidden controls. Read `serum-presets` sections
`new-preset-design` and `module-editing` after `workflow`: sources/wavetable
selection, sub/noise, both filters/routing, multiple envelopes/LFOs and matrix
routes, ordered/repeated FX blocks and voicing all require deliberate decisions.
Missing Live Configure controls are not a reason to stop at a manual recipe.
Retain useful baseline settings intentionally; do not enable everything by default.

For “make this preset faster/darker/bouncy” or another requested transformation,
read `serum-presets/existing-preset-edits`: unpack the existing preset to complete
JSON, edit a separate JSON, repack a separate preset and verify decoded changes.
Preserve unrelated state and the source; do not initialize an existing patch.

Original design reference, with a control coverage map and reproducible proposals.
Use the overview workflow and checklist. Controls listed here are not evidence
that they are mapped in Live or currently selected in a target instance.

## Identity

Scope: Serum **2**, checked against Xfer's official User Guide, software 2.0.18,
manual 1.0.3 (April 27, 2025), and online documentation on October 3, 2026.
Installed build remains unknown until observed. Later builds may change labels,
ranges and algorithms. Do not use Serum 1's two-oscillator/one-filter assumptions.
For authoritative exhaustive menu entries and advanced editor operations, use
the linked vendor manual; this is an original agent operating reference.

Locate OSC A/B/C, SUB, NOISE and FILTER 1/2 on the oscillator page; FX/MIXER for
racks and routing; ENV/LFO/MATRIX for movement; ARP/CLIP for generated notes;
GLOBAL for voice control, quality, preferences and tuning. Record track/device,
patch role and baseline. For live-instance edits read unfiltered
`get_device_parameters`; file-only creation inspects the template/reference state.
Parameter-name groups are inferred; host-reported names are not writable controls.

Always include `Serum 2 — manual settings` in final chat, even for suggestions.
Every intended but unapplied source, routing, FX or modulation setting belongs in
that table. Use `not applied — set manually`; list verified writes separately.
If a new patch needs Init, do it before other steps. Never Init an existing patch
just to implement an improvement recipe.

## Oscillators

OSC A, B and C each select Wavetable, Multisample, Sample, Granular or Spectral.
Decide mode first: the source selector and available controls depend on it.

| UI area / control | Design function | Specify in a recipe |
|---|---|---|
| Each oscillator: enable, mode, source | Establishes the generator | On/off; mode; exact table/instrument/sample name and category/path |
| OCT / SEMI / FINE and pitch tracking | Register, interval, tuning | Octaves, semitones, cents, tracking on/off and root pitch for samples |
| PHASE / RAND / phase-memory options | Note-start consistency or variation | Degrees, random amount and memory/retrigger behavior |
| UNISON / DETUNE / BLEND | Thickness and phase beating | Voice count; UI detune value; center-vs-side blend |
| Unison advanced options | Distribution and stereo image | Actual available mode, width, tuning distribution and other changed options |
| PAN / LEVEL | Placement and source balance | Center or signed pan, UI level % or displayed dB |
| WARP 1/2 selector and amount | Distorts/modulates the source before filtering | Exact mode, amount, order, modulator dependency and audible route |

Wavetable selection is a named asset; WT POS scans frames in that selected asset.
State its base frame/position and modulation range. A normalized position is not
a table-selection index. Frame counts vary; a fixed single-cycle sine/saw needs
no scanning. Never cycle table indices hoping to land on an unverified name.

For a basic oscillator choose a verified waveform/table, or manually construct
the required single-cycle waveform in the editor. `Basic Shapes` is a proposed
factory choice, not proof it exists in this installation; confirm the table name
and visible waveform before specifying a frame index.

Warp families serve different purposes: sync adds harmonics; bend/asymmetry and
PWM reshape a wave; mirror/remap alter waveform geometry; FM/AM/RM depend on a
modulator; phase distortion, folding, saturation and oscillator filtering change
harmonic balance. Retrieve the actual mode label before selecting it. FM from B
requires B to run even if its audible route is None; muting/removing the generator
may remove the modulation. Keep dual warp order and depths explicit.

### Wavetable editor and content

The editor supports drawing, harmonic/spectral editing, frame management,
interpolation/morphing, processing and audio/image/formula import. Specify the
resulting waveform/frame layout and processing intent, not undocumented menu
indices. A custom table recipe needs its export name/path and embedding/saving
step. Wavetable import differs from Sample mode playback; changing mode can alter
the sound and reset mode-specific settings. Most editor operations are manual.

### Multisample and Sample

| Mode | Controls to account for | Sound-design use |
|---|---|---|
| Multisample | Instrument/SFZ source; sample envelope, velocity tracking, randomization, timbre, unison, warp, pan/level | Acoustic or layered pitched foundation |
| Sample | Audio file/root/tracking; start/end, loop start/end/mode, crossfade, scan/rate, slicing/tails behavior, unison/warp | One-shots, loops, tape-like gestures |

Confirm actual file/library availability. Record start/end in the displayed unit
or as an explicitly defined fraction of file duration. A loop needs direction,
crossfade and a note-off behavior. SFZ multisample content is not interchangeable
with a single WAV. For transients preserve the start; for pads start after it.
Do not use warp, playback speed or time stretch as synonymous controls.

## Granular

Choose Granular on A/B/C, load a confirmed sample and establish its region and
root/tracking. The generator makes overlapping grains; sample selection and scan
position remain separate decisions.

| Control | What to decide |
|---|---|
| Start/end; loop menu/start/end/crossfade | Region, forward/reverse/loop behavior and seam smoothing |
| SCAN and X/Y control | Automatic movement versus manually selected position; path and rate |
| WINDOW amount | Grain-edge shape/smoothing; don't replace it with amplitude ADSR |
| DENSITY | Free Hz, BPM Sync division, or Grains count mode; value and mode together |
| DENSITY context options | Jump Start on/off; Max Grains cap for predictable CPU load |
| LENGTH | Free ms/s, BPM Sync division, or Percent of density period; Percent is unavailable in Grains density mode |
| OFFSET / DIR / PITCH randomization | Position variation, playback-direction variation and pitch scatter; note units |
| RAND LENGTH/PAN/LEVEL | Grain-duration, stereo and level variation |
| UNISON, WARP, PAN, LEVEL | Voice cost, timbral processing and balance |

Long grains and overlap often support smooth textures; short grains with sparse
or synced density can add detail. This is design reasoning, not an audible
diagnosis. Avoid large pitch randomization for harmonic pads. State Reverse
Grains and Jump Start if the intended attack/direction depends on them.

## Spectral

Choose Spectral and a confirmed audio source. This mode operates on resynthesized
frequency content rather than simply playing a WAV at a different speed.

Account for start/end, lower/upper analyzed frequency bounds, loop/crossfade,
X/Y placement, SCAN, CUT, FILTER, MIX, warp, unison and pan/level. CUT and FILTER
have mode-dependent behavior: specify the selected spectral processing mode and
its displayed value. Do not relabel them as a conventional oscillator low-pass
without confirmation. Separate temporal scanning from spectral frequency motion.
Retain the chosen asset/root/tracking and report every mode switch as a setting.

Use spectral scanning for frozen evolving timbres or unusual transition FX.
Give position/time and frequency endpoints; do not claim spectral resynthesis
has been implemented by writing only a configured mix knob.

## Routing

The oscillator/filter routing menus offer Filter, Main, Direct and None paths.
Filter routing can distribute signal to FILTER 1, FILTER 2 or both. Main enters
the main effects path; Direct bypasses filters and effects; None keeps a generator
out of the audible path and can support modulation-only use. BUS 1/2 send amounts
and bus output destinations must also be specified. [Vendor routing reference](https://xferrecords.com/web-manual/serum-2/routing-an-oscillator-or-filter).

SUB: waveform, pitch, phase, pan/level and route. A centered sine routed Direct
can provide an undistorted fundamental; do not assume every patch needs one.
NOISE: source name/path, one-shot/loop state, start/random start, pitch/fine,
tracking, pan/level and route. A noise oscillator can play sampled material,
so its name alone is not evidence of white noise.

FILTER 1/2: power, exact type, cutoff Hz, resonance %, drive, VAR function/value,
mix, key tracking and output routing. VAR changes meaning with type (e.g. a
second frequency or special filter characteristic); never guess from its label.
Families include low/high/band/notch, combinations, comb/flange, formant and
special models. Select the actual type label and slope from the installed menu.
Two enabled filters do not establish series routing; document the full path.
Tune comb/formant filters deliberately if the patch must follow harmony.

MIXER: trace source and filter routes, bus sends/returns, levels/pan and bus output
destinations. A parallel wet bus generally needs wet-only FX plus its send level;
an insert uses a wet/dry blend. Do not count a direct and bus dry signal twice.

## Modulation

ENV 1–4: attack, hold, decay, sustain, release and segment curves. ENV 1 controls
voice amplitude; other envelopes require destinations. Give ms/s for times and
the actual displayed sustain unit. Account for legato/retrigger overrides.

LFOs: type (Normal, Path, Chaos Lorenz/Rossler, S&H), drawn shape/path or chaos
settings, Free/Retrig/Envelope behavior, mono/poly operation, BPM/Hz, rate, phase,
delay/rise/smoothing as applicable, and any loopback. A one-shot LFO can become
an envelope; a free-running LFO need not restart per note. Chaos does not mean a
known periodic waveform. In an original proposal, define the curve explicitly.

MATRIX: source, optional auxiliary source/scaling, destination, depth, polarity,
curve and enabled state. Dragging a source can create a route but does not verify
its depth. Spell out base and min/max endpoint values when a depth number cannot
be translated reliably to physical units. Velocity, note number, wheel,
aftertouch, macros, random and expression sources should be chosen intentionally.
Oscillator/filter audio-rate sources require explicit routing prerequisites.

Macros: name the gesture, route every destination with endpoints/polarity, and
give its starting value. Unmapped macro assignments remain manual even if the
macro value is writable. Prefer a few expressive controls over constant movement
on every parameter. Patch FX process combined voices; envelope-driven FX can
retrigger when overlapping notes arrive, unlike a per-voice oscillator filter.

## Effects

FX has MAIN, BUS 1 and BUS 2 racks; processing order is top to bottom. Modules
may be repeated. Identify bus **and occurrence/slot**; `FX Param 3` is not a type.
Account for rack input/output routing, enabled/bypass, module type/preset, every
changed control, MIX and output LEVEL. “Default” means the named baseline/init
module from the observed build, not any unknown user-saved module default.

| Module | Controls to account for before prescribing it |
|---|---|
| Bode | Mono input, shift/range/direction/width, retrigger, delay BPM mode/time, feedback, balance, blur, mix/level |
| Chorus | Rate and BPM state, Delay 1/2 ms, depth, feedback, wet-filter LPF/HPF selector/cutoff, mix/level |
| Compressor | Single/multiband state, threshold, ratio, attack/release, gain, band settings if used, mix/level |
| Convolve | Exact impulse/file and embedding, size, tone, minimum-phase state, pre-delay/BPM, attack/decay/damp, IR gain, mix/level |
| Delay | Normal/Ping-Pong/Tap->Delay, quality, BPM/MS, L/R times and scalar offsets, link, feedback, FREQ/Q wet filter, mix/level |
| Distortion | Actual algorithm, drive, filter type/cutoff/resonance and pre/post placement, mix/level; changed shaper settings |
| Equalizer | Both band types, frequencies, Q and gains, output level |
| Filter | Exact model, cutoff/resonance/drive/VAR, tracking where available, mix/level; this processes summed voices |
| Flanger | Rate/BPM, depth, feedback, stereo phase, mix/level |
| Hyper/Dimension | Hyper voices/rate/detune/retrigger/wet; Dimension size/mix, output level |
| Phaser | Rate/BPM, poles, depth/depth 2, frequency, feedback, stereo phase, mix/level |
| Reverb | Selected algorithm and its own control set below, mix/level |
| Splitter L/H or L/M/H | Crossover frequencies, each branch's ordered modules/gain, recombination and phase considerations |
| Splitter MS | Mid/side branch processing and gain; restore to stereo intentionally |
| Utility | L/R polarity, LPF/HPF, mono-bass enable/frequency, width, pan, mix/level |

Reverb controls differ by algorithm. Plate uses lo/hi cuts, size, pre-delay, damp
and width. Hall adds a separate decay and spin rate/depth. Vintage has early
reflection size, decay, damp, diffusion A/B and chorus rate/depth. Nitrous has
feedback, diffusion, geometry mode and chorus. Basin has feedback and chorus.
Use the installed labels/units; SIZE is not universally a decay-in-seconds knob.

Distortion before filtering tames newly added harmonics; after filtering restores
edge. Chorus before reverb widens its input. Delay before reverb blurs echoes;
after reverb echoes the whole tail. These are design choices, not rules. A splitter
is a branching topology, so a linear FX list alone is incomplete.

## Performance

Specify polyphony limit, mono/legato state, portamento time/curve/always-on options
as applicable, pitch-bend up/down range and master output. Long releases plus
unison/grains can multiply voice cost; give a deliberate voice budget.

ARP: enable, slot/pattern, note order/range/octaves, rate/BPM, gate, swing, trigger,
reset/retrigger, velocity and graph/step behavior. CLIP: enable/slot, actual notes,
length, looping, timing and triggering. Internal sequences can change what a Live
MIDI clip produces; keep both off for a recipe driven entirely by external notes.

GLOBAL: Voice Control's selected oscillators, sequence length/voice offsets,
pan/detune/cutoff/envelope randomization; ENV/LFO scaling; render quality and
Serum 1 compatibility; concert pitch/tuning file/MTS-ESP state. Preserve tuning
unless requested. UI/help/update preferences are not sound-design parameters.
MPE requires appropriate input and explicit expression routes; a note clip alone
does not implement a gesture. MIDI mappings and Live Configure are separate.

## Recipes

These are **original proposed designs**, not factory patches or audible results.
All values below are manual targets until verified. Use the stated baseline and
retain its remaining controls; resolve unknown assets before dependent steps.

### Mystic Halo — new pitched FX texture

Purpose: a restrained, slow, upper-mid shimmer around sustained chord tones.
Start from Serum 2 Init **on the new track only**; internal ARP/CLIP off, clear
unused modulation, BUS 1/2 sends 0%, SUB/NOISE/C off, both warps off.

| Area | Target |
|---|---|
| OSC A | Wavetable, single-cycle triangle; proposed `Basic Shapes`, name/frame availability unknown/unverified — confirm triangle visually or create/save `Mystic Triangle`; OCT 0, SEMI 0, FINE 0 cents, tracking on, unison 3, detune 0.06 UI value, blend 70%, phase 0°, RAND 100%, pan center, level 55% |
| OSC B | Single-cycle sine, same confirmation rule; OCT +1, SEMI +7, FINE 0 cents, tracking on, unison 1, phase 0°, RAND 100%, pan center, level 14% |
| Routing/filter | A+B -> FILTER 1 -> MAIN; FILTER 1 on, proposed `MG Low 12` (confirm label), cutoff 1800 Hz, resonance 12%, drive 8%, mix 100%, key tracking 0%; FILTER 2 off |
| ENV 1 | Attack 1200 ms, hold 0 ms, decay 2400 ms, sustain 75%, release 3800 ms; Init curves |
| LFO 1 | Normal sine, 0.07 Hz, BPM off, Free, mono on; bipolar -> FILTER 1 cutoff: base 1800 Hz, endpoints 1400/2300 Hz; no delay/rise |
| LFO 2 | Normal sine, 0.11 Hz, BPM off, Free, mono on; bipolar -> OSC B level: base 14%, endpoints 10/18%; no delay/rise |
| MAIN FX slot 1 | Chorus on: BPM off, rate 0.18 Hz, Delay 1 8 ms, Delay 2 13 ms, depth 20%, feedback 8%, wet LPF 6000 Hz, mix 18%, level 0 dB |
| MAIN FX slot 2 | Delay on: Ping-Pong, quality on, BPM on, L/R base 1/8 notes, scalar offsets 1.5 (dotted), Link on, feedback 24%, wet FREQ 2500 Hz, Q 35% UI value, mix 14%, level 0 dB |
| MAIN FX slot 3 | Reverb Hall on: lo cut 35%, hi cut 30%, size 70%, pre-delay 30 ms, decay 4800 ms, spin rate 0.15 Hz, spin depth 12%, mix 28%, level 0 dB |
| Output/voices | Poly 12, Mono/Legato off, glide 0 ms, bend up/down 2 semitones; master -12 dB as a starting target, tune A=440 Hz; other global settings retain Init |
| Gesture | Mod wheel unipolar -> FILTER 1 cutoff from 1800 to 3500 Hz (in addition to LFO); wheel -> Hall mix from 28 to 38%; wheel starts at 0; other new routes absent |

Choose sparse MIDI notes from observed harmony, e.g. upper root/fifth held for
2–4 bars with overlap under one beat. Key unknown: propose notes conditionally
instead of inventing a scale. Audition at matched level and shorten tail/mix if
the texture obscures the lead. Include every unapplied row and its routes in chat.

### Bland existing patch — targeted options

Retain preset, source, existing FX and automation; do not apply Mystic Halo Init.
Recommendations depend on what is actually observed:

- **Static timbre:** if a multi-frame table is confirmed, add a sine LFO at 0.09 Hz,
  BPM off, Free, bipolar scanning ±5% of its full WT POS span around its observed
  base (reduce depth near boundaries). Keep pitch unchanged. If the source is
  single-cycle, propose cutoff motion instead: observed base to ±2 semitones of
  frequency, explicitly name the destination and limits.
- **Flat attack:** on a sustained patch with known filter type, propose ENV 2:
  attack 10 ms, hold 0, decay 350 ms, sustain 0%, release 200 ms; unipolar cutoff
  rise from observed base to one octave above, then back. Retain ENV 1. Do not
  add it blindly if existing envelope/matrix routes already perform this role.
- **Thin body:** add a quiet second source only after checking C/B availability;
  same octave as the main source, sine, single voice, -18 dB relative to the main
  oscillator, center, route through the same verified filter. Avoid octave-down
  layering when it competes with bass.
- **Limited expression:** wheel -> the verified cutoff base to +1 octave;
  optionally wheel -> one confirmed FX mix by +8 percentage points. Keep route
  amounts bounded and provide the complete manual mapping.

Start with one recommendation, match output level and listen in context. These
are hypotheses; unseen existing routing or source settings remain unknown.

## Saving

Save as a new user preset with a descriptive name; save source/table/IR files and
embed required content where offered. Do not overwrite an existing patch unless
requested. Save any useful FX rack/module presets separately if desired.
User-saved defaults can change new modules, so record a baseline rather than
assuming factory settings. Live Configure mappings should be saved with a
confirmed default configuration or rack if future instances need them.
`set_plugin_preset` is host program selection, not a general .serumpreset loader.
These save/embed/configuration steps remain manual unless actually verified.

## Sources

- [Official Serum 2 PDF manual](https://www.xferrecords.com/manual/serum-2/docs):
  version 2.0.18, manual 1.0.3; checked October 3, 2026. Primary reference for
  all control families above, including granular/spectral, FX and GLOBAL.
- [Official online guide](https://xferrecords.com/web-manual/serum-2/welcome)
  and [routing](https://xferrecords.com/web-manual/serum-2/routing-an-oscillator-or-filter).
- [Official Serum 2 overview](https://xferrecords.com/products/serum-2): synthesis
  mode overview; do not treat listed library content as an installed asset readback.

Vendor sources establish control behavior; recipes and musical recommendations
are original proposals. No vendor manual text or assets are bundled here.
