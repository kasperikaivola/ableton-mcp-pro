"""Ableton Live integration through the Model Context Protocol."""

__version__ = "0.1.0"

# Expose key classes and functions for easier imports
from .runtime import get_ableton_connection
from .connection import AbletonConnection
