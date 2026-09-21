"""Direct and importable entrypoint for the Ableton MCP server."""

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from MCP_Server import tools as _tools
    from MCP_Server.runtime import mcp
else:
    from . import tools as _tools
    from .runtime import mcp

__all__ = ["mcp", "main"]


def main():
    """Run the MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
