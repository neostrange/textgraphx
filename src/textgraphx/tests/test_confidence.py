"""Unit tests for confidence scoring and calibration utilities."""

import pytest

from textgraphx.confidence import calibrate_confidence, compute_evidence_weighted_confidence
from textgraphx.reasoning.confidence import calibrate_confidence as canonical_calibrate_confidence


def test_root_confidence_wrapper_reexports_canonical_calibration():
    assert calibrate_confidence is canonical_calibrate_confidence


@pytest.mark.unit
class TestConfidenceHelpers:
    def test_evidence_weighted_confidence_default_weights(self):
        score = compute_evidence_weighted_confidence(
            {
                "syntax": 0.9,
                "srl": 0.8,
                "temporal": 0.7,
                "ontology": 0.9,
            }
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.7

    def test_evidence_weighted_confidence_handles_empty(self):
        assert compute_evidence_weighted_confidence({}) == 0.0

    def test_calibrate_confidence_logistic(self):
        raw = 0.8
        calibrated = calibrate_confidence(raw, alpha=1.2, beta=-0.1, method="logistic")
        assert 0.0 <= calibrated <= 1.0

    def test_calibrate_confidence_affine(self):
        raw = 0.5
        calibrated = calibrate_confidence(raw, alpha=1.1, beta=0.1, method="affine")
        assert calibrated == pytest.approx(0.65)

    def test_calibrate_confidence_invalid_method_raises(self):
        with pytest.raises(ValueError):
            calibrate_confidence(0.5, method="unknown")
