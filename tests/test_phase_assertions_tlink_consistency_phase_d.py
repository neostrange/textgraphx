"""Phase-D tests for TLINK consistency assertions."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_after_tlinks_exposes_consistency_violation_label():
    from textgraphx.phase_assertions import PhaseAssertions

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 0}]

    result = PhaseAssertions(graph).after_tlinks()
    labels = [c["label"] for c in result.checks]
    assert "Unsuppressed contradictory TLINK pairs" in labels


@pytest.mark.unit
def test_after_tlinks_fails_when_consistency_violations_exceed_threshold():
    from textgraphx.phase_assertions import PhaseAssertions, PhaseThresholds

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    thresholds = PhaseThresholds(max_tlink_consistency_violations=0)
    result = PhaseAssertions(graph, thresholds=thresholds).after_tlinks()

    assert result.passed is False
    assert any("expected <= 0" in err for err in result.errors)
