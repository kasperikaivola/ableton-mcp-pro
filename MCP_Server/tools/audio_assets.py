"""Read-only wildcard discovery on the MCP server's local asset filesystem."""

import fnmatch
from functools import lru_cache
import json
import os
from pathlib import Path
import time

from mcp.server.fastmcp import Context

from ..runtime import mcp


def _matcher(pattern):
    if not isinstance(pattern, str) or not pattern.strip() or len(pattern) > 256:
        raise ValueError("pattern must contain 1..256 characters.")
    pattern = pattern.replace("\\", "/").casefold()
    parts = pattern.split("/")
    if pattern.startswith("/") or any(p in {"", ".", ".."} or ":" in p for p in parts):
        raise ValueError("Use a filename or root-relative wildcard, not an absolute/traversal path.")
    basename_only = len(parts) == 1

    def matches(relative):
        names = relative.replace("\\", "/").casefold().split("/")
        if basename_only:
            return fnmatch.fnmatchcase(names[-1], pattern)

        @lru_cache(maxsize=None)
        def match(i, j):
            if i == len(parts):
                return j == len(names)
            if parts[i] == "**":
                return match(i + 1, j) or (j < len(names) and match(i, j + 1))
            return (j < len(names) and fnmatch.fnmatchcase(names[j], parts[i])
                    and match(i + 1, j + 1))

        return match(0, 0)
    return matches


def _search(pattern, root_path, offset, limit, max_entries):
    matches_pattern = _matcher(pattern)
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a non-negative integer.")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100.")
    if type(max_entries) is not int or not 1 <= max_entries <= 1000000:
        raise ValueError("max_entries must be 1..1000000.")
    root = Path(root_path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root_path must be an accessible directory on the MCP server.")
    pending = [(root, 0)]
    found, examined, links, seen = [], 0, 0, 0
    errors = []
    stopped = None
    more = False
    response_chars = 0
    start = time.monotonic()
    while pending and not stopped and not more:
        directory, depth = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if examined >= max_entries or time.monotonic() - start >= 10:
                        stopped = "entry_limit" if examined >= max_entries else "time_limit"
                        break
                    examined += 1
                    try:
                        if entry.is_symlink():
                            links += 1
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            # Windows junctions are reparse points too, but may
                            # not be recognized as symlinks by older Python.
                            attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                            if attrs & 0x400:
                                links += 1
                            elif depth >= 64:
                                if len(errors) < 10:
                                    errors.append({"path": entry.path, "error": "Directory depth exceeds 64."})
                            else:
                                pending.append((Path(entry.path), depth + 1))
                            continue
                        relative = Path(entry.path).relative_to(root).as_posix()
                        if not entry.is_file(follow_symlinks=False) or not matches_pattern(relative):
                            continue
                        stat = entry.stat(follow_symlinks=False)
                        seen += 1
                        if seen <= offset:
                            continue
                        if len(found) >= limit:
                            more = True
                            break
                        extension = Path(entry.name).suffix.casefold()
                        item = {"file_path": entry.path, "relative_path": relative,
                                "bytes": stat.st_size, "extension": extension,
                                "serum_preset_candidate": extension == ".serumpreset",
                                "legacy_serum_fxp": extension == ".fxp"}
                        size = len(json.dumps(item, ensure_ascii=False))
                        if found and response_chars + size > 24000:
                            more = True
                            break
                        if size > 24000:
                            stopped = "result_path_too_long"
                            break
                        found.append(item)
                        response_chars += size
                    except OSError as exc:
                        if len(errors) < 10:
                            errors.append({"path": entry.path[:512], "error": str(exc)[:250]})
        except OSError as exc:
            if len(errors) < 10:
                errors.append({"path": str(directory)[:512], "error": str(exc)[:250]})
    complete = not stopped and not more and not errors and links == 0
    return {"root_path": str(root), "pattern": pattern, "offset": offset,
            "matches": found, "next_offset": offset + len(found) if more else None,
            "entries_examined": examined, "scan_complete": complete,
            "stop_reason": stopped or ("page_full" if more else "excluded_links_or_errors" if not complete else None),
            "skipped_links": links, "errors": errors,
            "instructions": "Filename patterns search at every depth; path patterns are root-relative with ** for zero or more folders. Follow next_offset for more matches. If scan limited, narrow root/pattern or raise max_entries; no exhaustive total is implied. Pagination rescans and may shift if files change. Paths are not Ableton browser URIs. .SerumPreset candidates need get_serum_preset_info validation; legacy .fxp is not supported by the Serum 2 editor."}


@mcp.tool()
def search_audio_assets(ctx: Context, pattern: str = "*.SerumPreset",
                        root_path: str = "G:/AudioAssets", offset: int = 0,
                        limit: int = 30, max_entries: int = 100000) -> str:
    """Find nested presets/audio files by case-insensitive wildcard on the server.

    Default library G:/AudioAssets. Filename patterns match recursively at all
    depths: *pad*.SerumPreset, *init*.SerumPreset, *atmos*.wav, *.fxp.
    Path patterns match relative folders: **/Serum*/**/*.SerumPreset; * and ?
    stay within a segment, ** matches zero or more folders, [] matches characters.
    Returns actual full paths, sizes, legacy FXP flags and next_offset pagination.
    Read-only; no preset payloads or audio decoded. Never invent a browser URI
    from results. Use get_serum_preset_info before editing a found Serum 2 file.
    Scan <=max_entries (1..1000000), <=10 seconds; limit 1..100. Incomplete/error
    coverage is explicit. Narrow root_path to a known subfolder for faster scans.
    Symlinks/junctions are excluded. No index; pagination may shift during changes.
    """
    try:
        return json.dumps(_search(pattern, root_path, offset, limit, max_entries), ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)[:1000]}, ensure_ascii=False)
