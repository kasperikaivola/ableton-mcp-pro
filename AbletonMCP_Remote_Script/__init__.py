from __future__ import absolute_import, print_function, unicode_literals

try:
    from .control_surface import AbletonMCP
except (ImportError, ValueError):
    from control_surface import AbletonMCP


def create_instance(c_instance):
    """Create and return the AbletonMCP script instance"""
    return AbletonMCP(c_instance)
