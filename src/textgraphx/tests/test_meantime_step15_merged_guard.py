"""Tests for Step 15: evaluator projection excludes merged TEvents from branch 3 fallback.

Verifies that the Frame-fallback branch (branch 3 in the event projection UNION)
correctly excludes TEvents with `merged=true` from its `NOT EXISTS` guard, so that
merged secondary events don't block the fallback while themselves being unprojectable.

Guards verified:
- Branch 3 Cypher includes `AND coalesce(ev.merged, false) = false` in NOT EXISTS
- `unmatched_gold_events` is present in MEANTIMEResults.to_dict()
- SRL diagnostics structure is present in MEANTIMEResults.to_dict() (step 16)

No live Neo4j required (source inspection only).
"""
from pathlib import Path
import pytest

EVALUATOR_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "meantime_evaluator.py"
)
BRIDGE_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "meantime_bridge.py"
)


@pytest.fixture(scope="module")
def evaluator_src() -> str:
    return EVALUATOR_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def bridge_src() -> str:
    return BRIDGE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 15: Branch 3 merged-event guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_branch3_has_not_exists_block(evaluator_src):
    """Branch 3 must have a NOT EXISTS clause to avoid duplicates."""
    assert "NOT EXISTS" in evaluator_src
    assert "MATCH (ev:TEvent)" in evaluator_src


@pytest.mark.unit
def test_branch3_checks_merged_false(evaluator_src):
    """Branch 3 NOT EXISTS must filter merged=false to avoid blocking fallback."""
    # The guard should appear in the NOT EXISTS block for branch 3
    assert "coalesce(ev.merged, false) = false" in evaluator_src


@pytest.mark.unit
def test_branch3_context_is_frame_fallback(evaluator_src):
    """Verify the merged guard is in the Frame fallback branch, not elsewhere."""
    # Branch 3 matches Frame nodes via PARTICIPATES_IN
    branch3_start = evaluator_src.find("[:PARTICIPATES_IN]->(f:Frame)")
    assert branch3_start != -1
    
    # Find the NOT EXISTS block after that match
    not_exists_start = evaluator_src.find("NOT EXISTS", branch3_start)
    assert not_exists_start != -1
    
    # The merged guard should appear between branch3_start and the next UNION or end
    next_section = evaluator_src.find("}", not_exists_start)
    guard_pos = evaluator_src.find("coalesce(ev.merged, false) = false", not_exists_start)
    
    assert not_exists_start < guard_pos < next_section


# ---------------------------------------------------------------------------
# Step 15: unmatched_gold_events diagnostic
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unmatched_gold_events_in_to_dict(bridge_src):
    """MEANTIMEResults.to_dict() must surface unmatched_gold_events."""
    assert "unmatched_gold_events" in bridge_src


@pytest.mark.unit
def test_unmatched_gold_pulls_from_predicted_document(bridge_src):
    """unmatched_gold_events comes from predicted_document.unmatched_gold_events."""
    assert "predicted_document.unmatched_gold_events" in bridge_src


# ---------------------------------------------------------------------------
# Step 16: SRL diagnostics in to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_srl_diagnostics_in_to_dict(bridge_src):
    """MEANTIMEResults.to_dict() must surface srl_diagnostics."""
    assert '"srl_diagnostics"' in bridge_src or "'srl_diagnostics'" in bridge_src


@pytest.mark.unit
def test_srl_diagnostics_inline_helper_exists(bridge_src):
    """_srl_diagnostics_inline() helper serializes the SRL report."""
    assert "_srl_diagnostics_inline" in bridge_src


@pytest.mark.unit
def test_srl_diagnostics_uses_asdict(bridge_src):
    """_srl_diagnostics_inline should use dataclasses.asdict for serialization."""
    assert "asdict" in bridge_src


# ---------------------------------------------------------------------------
# Integration: consolidated report structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidated_report_has_srl_field():
    """ConsolidatedQualityReport should accept srl_diagnostics."""
    from textgraphx.evaluation.meantime_bridge import ConsolidatedQualityReport
    from dataclasses import fields as dc_fields
    
    field_names = {f.name for f in dc_fields(ConsolidatedQualityReport)}
    assert "srl_diagnostics" in field_names


@pytest.mark.unit
def test_meantime_results_has_srl_field():
    """MEANTIMEResults should accept srl_diagnostics."""
    from textgraphx.evaluation.meantime_bridge import MEANTIMEResults, LayerScores
    from dataclasses import fields as dc_fields
    
    field_names = {f.name for f in dc_fields(MEANTIMEResults)}
    assert "srl_diagnostics" in field_names


@pytest.mark.unit
def test_meantime_results_serializes_srl_diagnostics():
    """MEANTIMEResults.to_dict() includes srl_diagnostics when present."""
    from textgraphx.evaluation.meantime_bridge import MEANTIMEResults, LayerScores
    from unittest.mock import MagicMock
    
    mock_srl = MagicMock()
    mock_srl.total_frames = 10
    
    results = MEANTIMEResults(
        doc_id="test",
        entity_strict=LayerScores("entity", True, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        entity_relaxed=LayerScores("entity", False, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        event_strict=LayerScores("event", True, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        event_relaxed=LayerScores("event", False, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        timex_strict=LayerScores("timex", True, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        timex_relaxed=LayerScores("timex", False, 1, 0, 0, 1.0, 1.0, 1.0, 1),
        srl_diagnostics=mock_srl,
    )
    
    d = results.to_dict()
    assert "srl_diagnostics" in d
    assert d["srl_diagnostics"] is not None
