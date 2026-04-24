"""Compatibility wrapper for the canonical reasoning provenance module."""

from textgraphx.reasoning.provenance import (
    stamp_inferred_relationships,
    validate_inferred_relationship_provenance,
)

__all__ = [
    "stamp_inferred_relationships",
    "validate_inferred_relationship_provenance",
]
