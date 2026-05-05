"""Tests for Step 12: temporal anchor diagnostics in SRLKGQualityEvaluator.

Verifies that ``TemporalAnchoringMetrics`` carries the three new Step-12 fields
and that ``_temporal_anchoring`` computes them with the correct Cypher patterns
and correct arithmetic.

Guards verified:
- TemporalAnchoringMetrics has events_with_time_anchor
- TemporalAnchoringMetrics has anchored_events_as_tlink_endpoint
- TemporalAnchoringMetrics has temporally_isolated_events
- TemporalAnchoringMetrics has anchor_tlink_yield_rate
- _temporal_anchoring populates all four fields
- Cypher queries reference HAS_TIME_ANCHOR
- Cypher guards against merged events
- NOT EXISTS block for temporally isolated events
- anchor_tlink_yield_rate is computed as anchored_tlink / events_with_anchor
- Zero-division safety: yield_rate = 0.0 when events_with_anchor = 0
- SRLKGQualityReport.temporal_anchoring reflects the new fields
- evaluate() returns a report that contains all Step-12 metrics

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from dataclasses import fields

import pytest

SRL_QUALITY_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "srl_kg_quality.py"
)


@pytest.fixture(scope="module")
def quality_src() -> str:
    return SRL_QUALITY_PATH.read_text(encoding="utf-8")


def _import_module():
    import importlib.util
    import sys
    mod_name = "srl_kg_quality_step12_test"
    spec = importlib.util.spec_from_file_location(mod_name, SRL_QUALITY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def quality_mod():
    return _import_module()


# ---------------------------------------------------------------------------
# Dataclass field existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_events_with_time_anchor_field(quality_mod):
    field_names = {f.name for f in fields(quality_mod.TemporalAnchoringMetrics)}
    assert "events_with_time_anchor" in field_names


@pytest.mark.unit
def test_anchored_events_as_tlink_endpoint_field(quality_mod):
    field_names = {f.name for f in fields(quality_mod.TemporalAnchoringMetrics)}
    assert "anchored_events_as_tlink_endpoint" in field_names


@pytest.mark.unit
def test_temporally_isolated_events_field(quality_mod):
    field_names = {f.name for f in fields(quality_mod.TemporalAnchoringMetrics)}
    assert "temporally_isolated_events" in field_names


@pytest.mark.unit
def test_anchor_tlink_yield_rate_field(quality_mod):
    field_names = {f.name for f in fields(quality_mod.TemporalAnchoringMetrics)}
    assert "anchor_tlink_yield_rate" in field_names


@pytest.mark.unit
def test_new_fields_default_to_zero(quality_mod):
    m = quality_mod.TemporalAnchoringMetrics()
    assert m.events_with_time_anchor == 0
    assert m.anchored_events_as_tlink_endpoint == 0
    assert m.temporally_isolated_events == 0
    assert m.anchor_tlink_yield_rate == 0.0


# ---------------------------------------------------------------------------
# Source: Cypher query patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_query_has_time_anchor(quality_src):
    assert "HAS_TIME_ANCHOR" in quality_src


@pytest.mark.unit
def test_query_merged_guard(quality_src):
    # Guard must appear in the anchor-related block
    assert "merged" in quality_src


@pytest.mark.unit
def test_query_not_exists_isolated(quality_src):
    assert "NOT EXISTS" in quality_src


@pytest.mark.unit
def test_query_anchor_tlink_yield_rate_computed(quality_src):
    assert "anchor_tlink_yield" in quality_src


@pytest.mark.unit
def test_all_four_new_fields_populated_in_source(quality_src):
    assert "events_with_time_anchor=events_with_anchor" in quality_src.replace(" ", "")
    assert "anchored_events_as_tlink_endpoint=anchor_tlink_ep" in quality_src.replace(" ", "")
    assert "temporally_isolated_events=isolated" in quality_src.replace(" ", "")
    assert "anchor_tlink_yield_rate=anchor_tlink_yield" in quality_src.replace(" ", "")


# ---------------------------------------------------------------------------
# Mock-based arithmetic: anchor_tlink_yield_rate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anchor_tlink_yield_rate_correct():
    mod = _import_module()
    mock_graph = MagicMock()

    # 7 candidates, 5 promoted, 3 tlink_endpoints, 2 nominal_anchored,
    # 4 events_with_anchor, 3 anchor_tlink_ep, 1 isolated
    call_returns = [
        [{"total": 7}],   # q_candidates
        [{"total": 5}],   # q_promoted
        [{"total": 3}],   # q_tlink_endpoint
        [{"total": 2}],   # q_nominal_anchored
        [{"total": 4}],   # q_anchored (events_with_time_anchor)
        [{"total": 3}],   # q_anchor_tlink
        [{"total": 1}],   # q_isolated
    ]
    idx = 0

    def side_effect(query, params):
        nonlocal idx
        result = MagicMock()
        result.data.return_value = call_returns[idx]
        idx += 1
        return result

    mock_graph.run.side_effect = side_effect

    evaluator = mod.SRLKGQualityEvaluator(mock_graph)
    metrics = evaluator._temporal_anchoring(None)

    assert metrics.events_with_time_anchor == 4
    assert metrics.anchored_events_as_tlink_endpoint == 3
    assert metrics.temporally_isolated_events == 1
    assert abs(metrics.anchor_tlink_yield_rate - 0.75) < 1e-9


@pytest.mark.unit
def test_anchor_tlink_yield_rate_zero_division_safe():
    mod = _import_module()
    mock_graph = MagicMock()

    call_returns = [
        [{"total": 0}],  # q_candidates
        [{"total": 0}],  # q_promoted
        [{"total": 0}],  # q_tlink_endpoint
        [{"total": 0}],  # q_nominal_anchored
        [{"total": 0}],  # q_anchored → 0 means yield = 0.0
        [{"total": 0}],  # q_anchor_tlink
        [{"total": 0}],  # q_isolated
    ]
    idx = 0

    def side_effect(query, params):
        nonlocal idx
        result = MagicMock()
        result.data.return_value = call_returns[idx]
        idx += 1
        return result

    mock_graph.run.side_effect = side_effect

    evaluator = mod.SRLKGQualityEvaluator(mock_graph)
    metrics = evaluator._temporal_anchoring(None)

    assert metrics.anchor_tlink_yield_rate == 0.0


# ---------------------------------------------------------------------------
# evaluate() integrates the new fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evaluate_returns_new_fields():
    mod = _import_module()
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = []

    evaluator = mod.SRLKGQualityEvaluator(mock_graph)
    report = evaluator.evaluate(doc_id=None)

    assert hasattr(report.temporal_anchoring, "events_with_time_anchor")
    assert hasattr(report.temporal_anchoring, "anchored_events_as_tlink_endpoint")
    assert hasattr(report.temporal_anchoring, "temporally_isolated_events")
    assert hasattr(report.temporal_anchoring, "anchor_tlink_yield_rate")


@pytest.mark.unit
def test_evaluate_report_type():
    mod = _import_module()
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = []

    evaluator = mod.SRLKGQualityEvaluator(mock_graph)
    report = evaluator.evaluate()

    assert isinstance(report.temporal_anchoring, mod.TemporalAnchoringMetrics)
