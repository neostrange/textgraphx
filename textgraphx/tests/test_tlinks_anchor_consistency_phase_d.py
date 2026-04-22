"""Phase-D tests for TLINK anchor consistency enforcement behavior."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_tlinks_recognizer_runs_anchor_consistency_query():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"suppressed_count": 2}]

    rows = obj.enforce_tlink_anchor_consistency()

    assert rows[0]["suppressed_count"] == 2
    assert obj.graph.run.called
    query = obj.graph.run.call_args[0][0]
    assert "MATCH (src)-[r:TLINK]->(dst)" in query
    assert "sourceAnchorType" in query
    assert "targetAnchorType" in query
    assert "anchorConsistency" in query
    assert "suppressedBy = 'tlink_anchor_consistency_filter'" in query


@pytest.mark.unit
def test_tlinks_recognizer_runs_anchor_consistency_shadow_query():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"inconsistent_count": 3, "self_link_count": 1, "endpoint_violation_count": 2}]

    rows = obj.enforce_tlink_anchor_consistency(shadow_only=True)

    assert rows[0]["inconsistent_count"] == 3
    query = obj.graph.run.call_args[0][0]
    assert "inconsistent_count" in query
    assert "self_link_count" in query
    assert "endpoint_violation_count" in query
    assert "suppressedBy = 'tlink_anchor_consistency_filter'" not in query


@pytest.mark.unit
def test_tlinks_wrapper_source_includes_anchor_consistency_call():
    from pathlib import Path

    src = Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")
    assert "Validate TLINK anchor consistency" in src
    assert "recognizer.enforce_tlink_anchor_consistency(shadow_only=tlink_shadow_mode)" in src
    assert "anchor_suppressed_tlinks" in src
    assert "anchor_shadow_inconsistencies" in src
