"""Compatibility wrapper for canonical TimeML relation helpers."""

from textgraphx.reasoning.temporal.timeml_relations import (
    CANONICAL_TLINK_RELTYPES,
    is_canonical_tlink_reltype,
    normalize_tlink_reltype,
)

__all__ = [
    "CANONICAL_TLINK_RELTYPES",
    "is_canonical_tlink_reltype",
    "normalize_tlink_reltype",
]
