"""Compatibility wrapper for the canonical reasoning fusion module."""

from textgraphx.reasoning.fusion import (
    fuse_entities_cross_document,
    fuse_entities_cross_sentence,
    propagate_coreference_identity_cross_document,
)

__all__ = [
    "fuse_entities_cross_document",
    "fuse_entities_cross_sentence",
    "propagate_coreference_identity_cross_document",
]
