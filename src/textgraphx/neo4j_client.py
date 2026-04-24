"""Compatibility wrapper for the canonical database client module."""

from textgraphx.database.client import (
    BoltGraphCompat,
    get_config_section,
    make_bolt_driver_from_config,
    make_graph_from_config,
)

__all__ = [
    "BoltGraphCompat",
    "get_config_section",
    "make_bolt_driver_from_config",
    "make_graph_from_config",
]
