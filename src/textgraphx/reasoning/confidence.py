"""Confidence scoring and calibration helpers for inferred graph edges."""

from __future__ import annotations

import math
from typing import Dict, Optional


DEFAULT_EVIDENCE_WEIGHTS: Dict[str, float] = {
    "syntax": 0.20,
    "srl": 0.20,
    "coref": 0.15,
    "temporal": 0.20,
    "ontology": 0.15,
    "lexical": 0.10,
}


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_evidence_weighted_confidence(
    evidence_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Compute weighted confidence from evidence family scores."""
    if not evidence_scores:
        return 0.0

    active_weights = dict(DEFAULT_EVIDENCE_WEIGHTS)
    if weights:
        active_weights.update({key: float(value) for key, value in weights.items()})

    weighted_sum = 0.0
    weight_total = 0.0
    for family, score in evidence_scores.items():
        weight = float(active_weights.get(family, 0.0))
        if weight <= 0.0:
            continue
        weighted_sum += weight * _clamp_01(score)
        weight_total += weight

    if weight_total <= 0.0:
        return 0.0
    return _clamp_01(weighted_sum / weight_total)


def calibrate_confidence(
    raw_confidence: float,
    alpha: float = 1.0,
    beta: float = 0.0,
    method: str = "logistic",
) -> float:
    """Apply a bounded calibration transform to raw confidence."""
    raw = _clamp_01(raw_confidence)
    normalized_method = str(method or "logistic").strip().lower()

    if normalized_method == "affine":
        return _clamp_01(alpha * raw + beta)
    if normalized_method != "logistic":
        raise ValueError("method must be one of: logistic, affine")

    eps = 1e-6
    probability = min(1.0 - eps, max(eps, raw))
    logit = math.log(probability / (1.0 - probability))
    calibrated = 1.0 / (1.0 + math.exp(-(alpha * logit + beta)))
    return _clamp_01(calibrated)


__all__ = [
    "DEFAULT_EVIDENCE_WEIGHTS",
    "calibrate_confidence",
    "compute_evidence_weighted_confidence",
]