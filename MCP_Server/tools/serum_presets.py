"""Offline full-state Serum 2 file tools; never access or alter Live instances."""

import json
from itertools import islice

from mcp.server.fastmcp import Context

from ..runtime import mcp
from .. import serum_preset_codec as codec
from .. import serum_preset_tree as tree


def _reply(action):
    try:
        result = action()
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(encoded) > 32000:
            for key in ("entries", "matches", "changes", "metadata", "modules"):
                if key in result:
                    del result[key]
            result["details_omitted"] = True
            result["note"] = "Response exceeded 32000 characters. Read/search/compare with a smaller limit/depth or narrower path. File writes, if reported, succeeded."
            encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(encoded) > 32000:
            # Even exotic, very long CBOR keys/asset paths cannot escape the cap.
            result = {key: result[key] for key in
                      ("live_applied", "dry_run", "change_count", "output_path",
                       "output_sha256", "output_bytes", "output_format") if key in result}
            result.update(details_omitted=True,
                          note="Response exceeded 32000 characters. Use a narrower scope/smaller page. Any reported output was written successfully.")
            encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        return encoded
    except Exception as exc:
        return json.dumps({"error": str(exc)[:1000], "live_applied": False}, ensure_ascii=False)


def _source(path):
    file, obj, sha, kind = codec.load(path)
    identity = {"file_path": str(file), "source_sha256": sha, "format": kind,
                "live_applied": False}
    return file, obj, sha, kind, identity


@mcp.tool()
def get_serum_preset_info(ctx: Context, file_path: str) -> str:
    """Inspect an offline Serum 2 .SerumPreset or packager JSON without dumping audio.

    Returns source SHA256 for guarded edits, metadata, module count and first 50
    module paths. Use read_serum_preset('/data') to paginate the whole inventory.
    Missing/default values and undocumented IDs are not resolved to GUI semantics.
    The file is not evidence of the currently loaded Live instance's state.

    For requested new presets, read get_synth_sound_design_guide with
    synth='serum-presets', sections workflow, new-preset-design and module-editing.
    Inspect the full design architecture, then actually write the new preset;
    missing Live Configure controls do not limit these offline file tools.
    For 'make this preset faster/darker/bouncy' or other existing-preset edits,
    read serum-presets/existing-preset-edits; unpack to JSON, edit and repack a
    separate preset. Suggestions alone remain read-only.
    For FX/matrix/wavetables and other hidden state, read serum-presets section
    complete-state-recipes. Guarded copy operations transfer complete reference
    subtrees/assets without sending huge values or truncated previews to chat.
    """
    def action():
        file, obj, sha, kind, result = _source(file_path)
        result.update(file_bytes=file.stat().st_size, metadata=tree.summary(obj["metadata"], 2),
                      module_count=len(obj["data"]),
                      modules=[{"path": "/data/" + tree.escape(k),
                                "value": tree.summary(v, 0)}
                               for k, v in islice(obj["data"].items(), 50)],
                      instructions="For new presets read serum-presets/workflow, new-preset-design and module-editing via get_synth_sound_design_guide. Design and write a separate .SerumPreset across sources, filters, envelopes, modulation, FX and voicing; missing Configure controls do not block offline edits. Existing transformations such as make it darker/faster/bouncy authorize edits: read existing-preset-edits, unpack to complete JSON, edit separate JSON and repack a separate preset. Preserve original/unrelated state and compare decoded changes. Read /data or search paths/values. Large arrays stay on disk. Use actual observed keys/enum strings; defaults, units and parameter validity are not inferred. Then load/audition in Serum; no Live state is changed by file generation.")
        return result
    return _reply(action)


@mcp.tool()
def read_serum_preset(ctx: Context, file_path: str, path: str = "",
                      offset: int = 0, limit: int = 30, depth: int = 2) -> str:
    """Read a bounded offline preset subtree using JSON Pointer, with child pagination.

    Root has /metadata and /data. Example /data/Env0/plainParams, or
    /data/FXRack0/FX/0. Escape slash in a key as ~1 and tilde as ~0.
    limit 1..100, offset >=0, depth 0..5. Values are summaries, not a packable
    document: expand returned paths. To read sample values use the exact channel
    array path with offset/limit. Unknown/default values remain unknown.
    """
    def action():
        _, obj, _, _, result = _source(file_path)
        result.update(tree.read(obj, path, offset, limit, depth))
        return result
    return _reply(action)


@mcp.tool()
def search_serum_preset(ctx: Context, file_path: str, query: str, path: str = "",
                        offset: int = 0, limit: int = 30,
                        include_array_values: bool = False) -> str:
    """Search offline preset paths and scalar values (case-insensitive literal).

    Find controls, enum strings, asset paths, modulation or FX; results include
    exact pointers for reads/edits. Scope with path, paginate using next_offset.
    Large scalar arrays (>64 entries) are skipped by default and reported; explicit
    include_array_values=true includes them. No synth parameter mapping is guessed.
    """
    def action():
        _, obj, _, _, result = _source(file_path)
        result.update(tree.search(obj, query, path, offset, limit, include_array_values))
        return result
    return _reply(action)


@mcp.tool()
def edit_serum_preset(ctx: Context, file_path: str, expected_sha256: str,
                      operations: list[dict], output_path: str = "",
                      output_format: str = "preset", dry_run: bool = True,
                      overwrite: bool = False) -> str:
    """Guarded offline edits preserving all other preset fields and embedded assets.

    operations: [{"op":"replace","path":"/data/Env0/plainParams/kParamDecay",
                  "value":0.6}]. Supports JSON Patch add/replace/remove/test/copy.
    copy: {"op":"copy","from":"/data/Oscillator0/WTOsc0",
           "path":"/data/Oscillator0/WTOsc0",
           "source_file_path":"reference.SerumPreset","source_sha256":"..."}.
    Omit both source fields to copy from the currently edited document. A reference
    needs its own inspected SHA256. Copies transfer complete decoded subtrees,
    including huge embedded assets and opaque CBOR, without chat previews. Array
    copies insert (/- appends); object copies set/replace. No automatic ID remapping.
    add on an array inserts, '-' appends; add on an object sets/replaces its key.
    All parents must exist. Read actual paths first; a 'default' string must be
    explicitly replaced with an object before adding parameters. No GUI ranges,
    enums/defaults or units are invented/validated. Use known-good preset examples
    or controlled before/after exports for unfamiliar controls.
    New sound creation should edit its defining oscillator/source, filter,
    envelope/LFO, modulation, FX and voicing state, not just rename a template or
    change one knob. Read serum-presets/new-preset-design and module-editing for
    coherent asset selection, complete FX slots and coupled matrix destinations.
    Require source SHA256 from info/read/search. Default dry_run previews a full
    validated/encoded batch without writing. dry_run=false requires a separate
    .SerumPreset (output_format=preset) or .json output. Never overwrites source.
    Existing outputs require overwrite=true. Metadata hash is preserved as opaque;
    no vendor checksum algorithm is inferred. This edits files, not loaded Serum.
    A successful dry-run is not delivery: for an authorized creation request,
    publish with dry_run=false to a separate output and compare decoded changes.
    For an existing-preset transformation, default to the JSON round trip:
    unpack via convert_serum_preset, edit that JSON with output_format='json',
    then repack the edited JSON. Use each inspected input's own SHA256.
    """
    def action():
        file, obj, sha, _, result = _source(file_path)
        if expected_sha256 != sha:
            raise ValueError("Source SHA256 differs; inspect the current file before editing.")
        if len(json.dumps(operations, allow_nan=False)) > 1024 * 1024:
            raise ValueError("Operation batch exceeds 1 MiB; use file conversion for large asset edits.")
        donors = {}

        def resolve_copy(op):
            donor_path, expected = op.get("source_file_path"), op.get("source_sha256")
            if not isinstance(donor_path, str) or not donor_path or not isinstance(expected, str) or not expected:
                raise ValueError("External copy requires source_file_path and source_sha256.")
            cache_key = (donor_path, expected)
            if cache_key not in donors:
                donor_file, donor_obj, donor_sha, _ = codec.load(donor_path)
                if donor_sha != expected:
                    raise ValueError("Copy source SHA256 differs; inspect the reference again.")
                donors[cache_key] = (donor_file, donor_obj, donor_sha)
            return tree.get(donors[cache_key][1], op["from"])

        edited, changes = tree.patch(obj, operations, copy_resolver=resolve_copy)
        raw = codec.encode(edited, output_format)
        # Decode the produced bytes before publication, validating the container.
        codec.decode(raw)
        for donor_file, _, donor_sha in donors.values():
            if codec.digest(donor_file.read_bytes()) != donor_sha:
                raise ValueError("Copy source changed while processing; no output written.")
        result.update(dry_run=dry_run, changes=changes, change_count=len(changes),
                      output_format=output_format, encoded_bytes=len(raw),
                      note="Decoded values preserved outside explicit operations. Re-encoding may change binary bytes. Load/audition the output manually; the running instance is unchanged.")
        if not dry_run:
            if not output_path:
                raise ValueError("output_path is required when dry_run=false.")
            result.update(codec.write_output(file, output_path, raw, output_format, overwrite, sha))
        return result
    return _reply(action)


@mcp.tool()
def convert_serum_preset(ctx: Context, file_path: str, output_path: str,
                         output_format: str, expected_sha256: str,
                         overwrite: bool = False) -> str:
    """Extract complete Serum 2 state to JSON on disk, or repackage JSON to preset.

    output_format='json' (unpack) or 'preset' (pack); target extension must match.
    Accepts either format as input. Uses source SHA256 from inspection; separate
    outputs only. Embedded assets are preserved; full JSON is never sent to chat.
    Non-JSON CBOR types explicitly block JSON export; edit binary instead to retain
    them. Source preserved, existing output requires overwrite=true. No Live load.
    Default for 'make this preset faster/darker/bouncy' and other edit requests:
    unpack existing preset to JSON, edit a separate JSON, then repack to a separate
    .SerumPreset. Read serum-presets/existing-preset-edits for the full sequence.
    Each conversion requires the SHA256 of its own input, including edited JSON.
    """
    def action():
        file, obj, sha, _, result = _source(file_path)
        if expected_sha256 != sha:
            raise ValueError("Source SHA256 differs; inspect the file again.")
        raw = codec.encode(obj, output_format)
        codec.decode(raw)
        result.update(codec.write_output(file, output_path, raw, output_format, overwrite, sha))
        return result
    return _reply(action)


@mcp.tool()
def compare_serum_presets(ctx: Context, left_path: str, right_path: str,
                          path: str = "", offset: int = 0, limit: int = 30) -> str:
    """Compare decoded Serum preset/JSON state; report bounded changed pointers.

    Use for confirming an edit changes only intended controls while preserving
    audio/unknown fields, or learning mappings from controlled manual exports.
    Scope with JSON Pointer and paginate using next_offset. Equal decoded state
    does not require byte-identical compression. No audible/live verification.
    """
    def action():
        _, left, lsha, _, _ = _source(left_path)
        _, right, rsha, _, _ = _source(right_path)
        result = tree.compare(left, right, path, offset, limit)
        result.update(left_sha256=lsha, right_sha256=rsha, live_applied=False)
        return result
    return _reply(action)
