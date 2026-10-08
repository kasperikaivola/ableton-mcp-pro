"""Experimental same-build SerumPreset -> VST3 preset packager; not an MCP tool.

Uses a real Serum .vstpreset for class identity and processor/controller schemas.
No vendor binary patching, private addresses, or Live state changes.
Container layout: Steinberg public SDK source/vst/vstpresetfile.cpp.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from MCP_Server import serum_preset_codec as codec


def read_vst(raw):
    if len(raw) < 48 or raw[:8] != b"VST3\x01\0\0\0":
        raise ValueError("Expected VST3 preset container version 1")
    class_id = raw[8:40]
    int(class_id, 16)
    offset = struct.unpack_from("<q", raw, 40)[0]
    if not 48 <= offset <= len(raw) - 8 or raw[offset:offset + 4] != b"List":
        raise ValueError("Invalid chunk-list offset")
    count = struct.unpack_from("<i", raw, offset + 4)[0]
    if not 1 <= count <= 128 or offset + 8 + count * 20 != len(raw):
        raise ValueError("Invalid chunk list")
    chunks = {}
    spans = []
    for i in range(count):
        tag, start, size = struct.unpack_from("<4sqq", raw, offset + 8 + i * 20)
        if tag in chunks or start < 48 or size <= 0 or start + size > offset:
            raise ValueError("Invalid/duplicate chunk")
        if any(start < b and start + size > a for a, b in spans):
            raise ValueError("Overlapping chunks")
        spans.append((start, start + size))
        chunks[tag] = raw[start:start + size]
    return class_id, chunks


def unpack_state(raw):
    if not raw.startswith(codec.MAGIC):
        raise ValueError("Expected Serum XferJson state")
    length = struct.unpack_from("<Q", raw, 9)[0]
    end = 17 + length
    decoded, encoding = struct.unpack_from("<II", raw, end)
    if encoding != 2 or decoded > codec.MAX_BYTES:
        raise ValueError("Unsupported state payload")
    cbor, zstd = codec.libraries()
    data = zstd.ZstdDecompressor().decompress(raw[end + 8:], max_output_size=decoded)
    if len(data) != decoded:
        raise ValueError("State length mismatch")
    return json.loads(raw[17:end]), cbor.loads(data)


def pack_state(meta, data):
    cbor, zstd = codec.libraries()
    payload = cbor.dumps(data)
    compressed = zstd.ZstdCompressor(level=3).compress(payload)
    # Observed in both processor/controller chunks of the supplied native host preset.
    meta = dict(meta, hash=hashlib.md5(compressed).hexdigest())
    header = json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode()
    return (codec.MAGIC + struct.pack("<Q", len(header)) + header
            + struct.pack("<II", len(payload), 2) + compressed)


def build(source, template, output):
    source, preset, source_sha, _ = codec.load(str(source))
    template = template.resolve(strict=True)
    template_raw = template.read_bytes()
    template_sha = codec.digest(template_raw)
    class_id, chunks = read_vst(template_raw)
    schemas = {}
    for tag, component in ((b"Comp", "processor"), (b"Cont", "controller")):
        meta, data = unpack_state(chunks[tag])
        if meta.get("product") != "Serum2" or meta.get("component") != component:
            raise ValueError("Template is not a Serum processor/controller pair")
        for key in ("productVersion", "version"):
            if meta.get(key) != preset["metadata"].get(key):
                raise ValueError(f"Source/template {key} differs; no cross-build conversion")
        schemas[tag] = meta, data
    known = set().union(*(data for _, data in schemas.values()))
    metadata_keys = {"fileType", "presetName", "presetAuthor", "presetDescription"}
    unsupported = set(preset["data"]) - known - metadata_keys
    if unsupported:
        raise ValueError(f"Source fields absent from template schemas: {sorted(unsupported)}")
    report = {"source": str(source), "source_sha256": source_sha,
              "template": str(template), "template_sha256": template_sha,
              "class_id": class_id.decode(), "version": preset["metadata"]["productVersion"],
              "experimental": True, "live_applied": False, "chunks": {}}
    for tag, (meta, baseline) in schemas.items():
        data = {key: copy.deepcopy(preset["data"].get(key, value))
                for key, value in baseline.items()}
        # The component role is host state, not the file's SerumPreset identity.
        data["component"] = meta["component"]
        if tag == b"Cont":
            for key in ("presetName", "presetAuthor", "presetDescription"):
                value = preset["metadata"].get(key, "")
                meta[key] = value
                if key in data:
                    data[key] = value
            if "presetHasBeenEdited" in data:
                data["presetHasBeenEdited"] = False
        chunks[tag] = pack_state(meta, data)
        assert unpack_state(chunks[tag])[1] == data
        report["chunks"][tag.decode()] = {"bytes": len(chunks[tag]),
            "source_keys": sorted(set(baseline) & set(preset["data"])),
            "retained_host_keys": sorted(set(baseline) - set(preset["data"]))}
    payload = bytearray(b"VST3" + struct.pack("<i", 1) + class_id + b"\0" * 8)
    entries = []
    for tag, chunk in chunks.items():
        entries.append((tag, len(payload), len(chunk)))
        payload.extend(chunk)
    struct.pack_into("<q", payload, 40, len(payload))
    payload.extend(b"List" + struct.pack("<i", len(entries)))
    for entry in entries:
        payload.extend(struct.pack("<4sqq", *entry))
    assert read_vst(bytes(payload)) == (class_id, chunks)
    output = output.absolute()
    if output.suffix.lower() != ".vstpreset" or output.resolve() in (source, template):
        raise ValueError("Choose a separate .vstpreset output")
    if codec.digest(source.read_bytes()) != source_sha or codec.digest(template.read_bytes()) != template_sha:
        raise ValueError("Input changed during packaging")
    with output.open("xb") as stream:
        stream.write(payload)
    report.update(output=str(output), output_sha256=codec.digest(payload), output_bytes=len(payload))
    return report


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build(args.source, args.template, args.output)
    args.output.with_suffix(".report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("output", "output_bytes", "version", "class_id")}, indent=2))
