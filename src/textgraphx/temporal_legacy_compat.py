"""Compatibility wrapper for canonical TemporalPhase legacy helpers."""

from textgraphx.reasoning.temporal.legacy_compat import (
    LEGACY_METHODS,
    legacy_event_mentions,
    legacy_event_to_event_links,
    legacy_event_to_time_links,
)

__all__ = [
    "LEGACY_METHODS",
    "legacy_event_mentions",
    "legacy_event_to_event_links",
    "legacy_event_to_time_links",
]
