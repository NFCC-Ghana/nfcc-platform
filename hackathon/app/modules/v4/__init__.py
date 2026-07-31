"""
V4 modules for the NFCC Platform
"""

try:
    from .situation_map import (
        render_situation_map,
        render_minimal_map,
        render_map_fallback,
    )

    __all__ = ["render_situation_map", "render_minimal_map", "render_map_fallback"]
except ImportError:
    # If situation_map doesn't exist yet, define empty functions
    def render_situation_map(*args, **kwargs):
        return None

    __all__ = ["render_situation_map"]
