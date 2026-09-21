"""Production source-size guard for the module refactor."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE_LINES = 1000
EXCLUDED_PARTS = {"__pycache__", "tests", "docs"}


def production_source_files():
    roots = (
        (ROOT / "MCP_Server", "*.py"),
        (ROOT / "AbletonMCP_Remote_Script", "*.py"),
        (ROOT / "MaxForLive" / "code", "*.js"),
    )
    paths = []
    for root, pattern in roots:
        paths.extend(
            path
            for path in root.rglob(pattern)
            if not EXCLUDED_PARTS.intersection(path.parts)
            and path.suffix.lower() != ".amxd"
        )
    return sorted(paths)


def line_count(path):
    return len(path.read_text(encoding="utf-8").splitlines())


def test_production_sources_are_at_most_1000_lines():
    oversized = {
        str(path.relative_to(ROOT)): line_count(path)
        for path in production_source_files()
        if line_count(path) > MAX_SOURCE_LINES
    }
    assert oversized == {}, (
        "Production source files over the 1,000-line ceiling: "
        + repr(oversized)
    )
