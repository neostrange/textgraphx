"""Compatibility wrapper for the canonical reasoning confidence module."""

from textgraphx.reasoning.confidence import (
    DEFAULT_EVIDENCE_WEIGHTS,
    calibrate_confidence,
    compute_evidence_weighted_confidence,
)

__all__ = [
    "DEFAULT_EVIDENCE_WEIGHTS",
    "calibrate_confidence",
    "compute_evidence_weighted_confidence",
]
