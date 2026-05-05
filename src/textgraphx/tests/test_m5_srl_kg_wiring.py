"""Tests for the SRL KG quality sub-metrics wired into the M5 semantic-category
evaluator (semantic_category_evaluator.py).

Covers:
- `evaluate_srl_quality` method exists on SemanticCategoryEvaluator
- `evaluate_srl_quality` delegates to SRLKGQualityEvaluator with correct doc_id
- `evaluate_srl_quality` returns None gracefully when SRLKGQualityEvaluator raises
- `create_semantic_category_report` accepts optional doc_id keyword argument
- `create_semantic_category_report` includes srl_quality key in evidence
- `create_semantic_category_report` includes srl_quality_available in feature_activation_evidence
- SRL sub-metrics appear in metrics dict when SRL report is available
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from textgraphx.evaluation.semantic_category_evaluator import (
    SemanticCategoryEvaluator,
    create_semantic_category_report,
)
from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.srl_kg_quality import (
    SRLKGQualityReport,
    FrameCoverageMetrics,
    ArgumentDensityMetrics,
    ConfidenceCalibrationMetrics,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_run_metadata() -> RunMetadata:
    return RunMetadata(
        dataset_hash="abc",
        config_hash="xyz",
        seed=42,
        strict_gate_enabled=True,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-05-02T00:00:00Z",
    )


def _make_mock_graph():
    """Graph that returns empty result sets for all Cypher calls."""
    g = MagicMock()
    g.run.return_value.data.return_value = [{"c": 0}]
    return g


def _make_srl_report(doc_id="test_doc") -> SRLKGQualityReport:
    return SRLKGQualityReport(
        doc_id=doc_id,
        coverage=FrameCoverageMetrics(
            total_sentences=10,
            total_frames=25,
            propbank_frames=18,
            nombank_frames=7,
            frames_per_sentence=2.5,
        ),
        density=ArgumentDensityMetrics(
            total_frames=25,
            total_arguments=60,
            args_per_frame=2.4,
        ),
        calibration=ConfidenceCalibrationMetrics(
            total_frames_with_conf=20,
            provisional_frames=3,
            provisional_rate=0.15,
            mean_confidence=0.72,
            confidence_histogram={"[0.7,0.9)": 14, "[0.9,1.0]": 3, "[0.5,0.7)": 3},
        ),
        aligns_with_count=4,
    )


# ---------------------------------------------------------------------------
# Method-existence / delegation tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_evaluate_srl_quality_method_exists():
    """SemanticCategoryEvaluator must expose evaluate_srl_quality."""
    g = _make_mock_graph()
    evaluator = SemanticCategoryEvaluator(g)
    assert hasattr(evaluator, "evaluate_srl_quality"), \
        "SemanticCategoryEvaluator missing evaluate_srl_quality"
    assert callable(evaluator.evaluate_srl_quality)


@pytest.mark.unit
def test_evaluate_srl_quality_delegates_doc_id():
    """evaluate_srl_quality must pass doc_id through to SRLKGQualityEvaluator.evaluate."""
    g = _make_mock_graph()
    evaluator = SemanticCategoryEvaluator(g)

    fake_report = _make_srl_report("my_doc")
    mock_inner = MagicMock()
    mock_inner.evaluate.return_value = fake_report

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        return_value=mock_inner,
    ):
        result = evaluator.evaluate_srl_quality(doc_id="my_doc")

    mock_inner.evaluate.assert_called_once_with(doc_id="my_doc")
    assert result is fake_report


@pytest.mark.unit
def test_evaluate_srl_quality_passes_graph_to_inner_evaluator():
    """SemanticCategoryEvaluator must pass its graph to SRLKGQualityEvaluator.__init__."""
    g = _make_mock_graph()
    evaluator = SemanticCategoryEvaluator(g)

    mock_cls = MagicMock()
    mock_cls.return_value.evaluate.return_value = _make_srl_report()

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        mock_cls,
    ):
        evaluator.evaluate_srl_quality(doc_id="d1")

    mock_cls.assert_called_once_with(g)


@pytest.mark.unit
def test_evaluate_srl_quality_returns_none_on_exception():
    """evaluate_srl_quality must return None (not raise) when inner evaluator fails."""
    g = _make_mock_graph()
    evaluator = SemanticCategoryEvaluator(g)

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        side_effect=RuntimeError("service unavailable"),
    ):
        result = evaluator.evaluate_srl_quality(doc_id="x")

    assert result is None


# ---------------------------------------------------------------------------
# create_semantic_category_report: doc_id parameter and srl_kg embedding
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_semantic_category_report_accepts_doc_id():
    """create_semantic_category_report must accept an optional doc_id kwarg."""
    meta = _make_run_metadata()
    g = _make_mock_graph()
    # Should not raise
    report = create_semantic_category_report(meta, g, doc_id="my_doc")
    assert report.metric_type == "semantic_category_metrics"


@pytest.mark.unit
def test_create_semantic_category_report_includes_srl_quality_in_evidence():
    """Report evidence must contain 'srl_quality' key."""
    meta = _make_run_metadata()
    g = _make_mock_graph()
    report = create_semantic_category_report(meta, g)
    assert "srl_quality" in report.evidence, \
        "create_semantic_category_report missing 'srl_quality' in evidence"


@pytest.mark.unit
def test_create_semantic_category_report_srl_quality_available_in_feature_activation():
    """'srl_quality_available' must appear in feature_activation_evidence."""
    meta = _make_run_metadata()
    g = _make_mock_graph()
    report = create_semantic_category_report(meta, g)
    fa = report.validity_header.feature_activation_evidence
    assert "srl_quality_available" in fa, \
        "create_semantic_category_report missing 'srl_quality_available' in feature_activation_evidence"


@pytest.mark.unit
def test_create_semantic_category_report_srl_metrics_in_metrics_dict_when_available():
    """When SRL report is available, srl_* keys must appear in metrics."""
    meta = _make_run_metadata()
    g = _make_mock_graph()

    fake_report = _make_srl_report()
    mock_inner = MagicMock()
    mock_inner.evaluate.return_value = fake_report

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        return_value=mock_inner,
    ):
        report = create_semantic_category_report(meta, g, doc_id="test_doc")

    expected_keys = [
        "srl_frames_per_sentence",
        "srl_propbank_frames",
        "srl_nombank_frames",
        "srl_args_per_frame",
        "srl_provisional_rate",
        "srl_mean_confidence",
        "srl_aligns_with_count",
    ]
    for key in expected_keys:
        assert key in report.metrics, f"Missing expected SRL metric key: {key!r}"


@pytest.mark.unit
def test_create_semantic_category_report_srl_metric_values_match_report():
    """SRL sub-metric values in report must match the SRLKGQualityReport fields."""
    meta = _make_run_metadata()
    g = _make_mock_graph()

    fake_report = _make_srl_report()
    mock_inner = MagicMock()
    mock_inner.evaluate.return_value = fake_report

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        return_value=mock_inner,
    ):
        report = create_semantic_category_report(meta, g, doc_id="test_doc")

    assert report.metrics["srl_frames_per_sentence"] == pytest.approx(2.5)
    assert report.metrics["srl_propbank_frames"] == 18
    assert report.metrics["srl_nombank_frames"] == 7
    assert report.metrics["srl_args_per_frame"] == pytest.approx(2.4)
    assert report.metrics["srl_provisional_rate"] == pytest.approx(0.15)
    assert report.metrics["srl_mean_confidence"] == pytest.approx(0.72)
    assert report.metrics["srl_aligns_with_count"] == 4


@pytest.mark.unit
def test_create_semantic_category_report_srl_quality_false_when_unavailable():
    """When SRLKGQualityEvaluator raises, srl_quality_available must be False."""
    meta = _make_run_metadata()
    g = _make_mock_graph()

    with patch(
        "textgraphx.evaluation.semantic_category_evaluator.SRLKGQualityEvaluator",
        side_effect=ImportError("not installed"),
    ):
        report = create_semantic_category_report(meta, g, doc_id="d")

    fa = report.validity_header.feature_activation_evidence
    assert fa["srl_quality_available"] is False
