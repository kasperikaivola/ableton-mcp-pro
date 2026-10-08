# Serum VST3 loading prototype — experimental

The bounded test succeeded on 2026-10-07 with Serum 2.0.16 and Live 12.4.
This is research code, not a registered/general-purpose MCP loading tool.

`build.py` packages a `.SerumPreset` with the class identity and processor/
controller schemas from a native same-build Serum `.vstpreset`. It rejects
cross-version inputs, unmapped top-level source fields and existing output files.
It preserves source/template files, rebuilding Comp/Cont and retaining the Info
chunk. It does not claim arbitrary preset/module/version compatibility.

Example from the repository root:

```powershell
.venv/Scripts/python.exe artifacts/vstpreset-prototype/build.py "H:/gitprojects/serum-preset-packager/converted-examples/Bass - 777/Bass - 777.SerumPreset" "C:/Users/kaspe/Documents/Ableton/User Library/Serum 2 128 Controls.vstpreset" "artifacts/vstpreset-prototype/MCP Serum Loading Test - Bass 777.vstpreset"
```

The generated file was copied to the User Library and discovered through
`get_browser_items_at_path(path="user_library")`. Its returned URI was:

```text
query:UserLibrary#MCP%20Serum%20Loading%20Test%20-%20Bass%20777.vstpreset
```

`load_instrument_or_effect` loaded that item onto a new MIDI track,
`MCP Preset Loading Test` (index 14), producing Serum 2 at device index 0.
The test track and User Library preset remain available for user inspection.
No existing tracks/clips were edited, no MIDI was added, and no transport or
global tempo changes or project save was requested/performed.

## Evidence

- `MCP Serum Loading Test - Bass 777.report.json`: input/output hashes, version,
  class ID and module-key partitioning.
- `MCP Serum Loading Test - Bass 777.native-check.json`: separate native processor
  accepted the Comp state; 32 explicitly serialized parameter values matched,
  and FX order was Distortion → EQ → Filter. Another 36 expected values were
  omitted in native serialization and remain unverified by that comparison.
- `live-readback.json`: the new device's complete unfiltered 124-parameter
  Configure inventory (including Device On), obtained through MCP after loading.
- `live-verification.json`: 29 selected live parameter values matched source
  state, and source/template SHA256 remained unchanged. Includes both oscillator
  levels/octaves/enables, sub state, two envelopes, filter values, mono and legato.

The source was found in `converted-examples` because the formerly checked fixture
folders had been reorganized. No source/library input preset was modified.

## Limits and next implementation

The minimal headless research host crashed while applying component state to a
separately instantiated controller. `verify_native.py` therefore checks only the
processor via public VST3 interfaces; it reuses optional local research host
helpers from the sibling packager repository. It does not attach to Live.
The real Ableton browser load and subsequent parameter reads succeeded.

Full live GUI/controller state, wavetable asset identity, modulation/FX controls
and audio equivalence were not verified. Existing-device replacement, automation
preservation and builds other than 2.0.16 were not tested. Native readback is not
an audio audition. Template-dependent fields still need broader semantic review
before this converter becomes a supported API.

A production MCP tool needs a supported native template/version strategy,
bounded validation/atomic publication, browser discovery/indexing and explicit
load/readback status. New-instance loading is demonstrated; safe replacement of
an existing device remains separate work.

The container layout is based on the
[Steinberg VST3 preset implementation](https://github.com/steinbergmedia/vst3_public_sdk/blob/master/source/vst/vstpresetfile.cpp).
The Serum state transformation is independently derived from the locally supplied
native host preset; no third-party converter implementation was copied.
