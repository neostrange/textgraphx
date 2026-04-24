"""Phase-B tests for TimeML completeness checks in temporal assertions."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_after_temporal_exposes_timeml_completeness_labels():
    from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 0}]

    result = PhaseAssertions(graph).after_temporal()
    labels = [c["label"] for c in result.checks]

    assert "TEvent nodes missing core TimeML fields" in labels
    assert "TIMEX nodes missing core TimeML fields" in labels
    assert "Signal nodes missing text/span fields" in labels
    assert "TLINK relationships missing relTypeCanonical" in labels


@pytest.mark.unit
def test_after_temporal_fails_when_missing_counts_exceed_thresholds():
    from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions, PhaseThresholds

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 2}]

    thresholds = PhaseThresholds(
        max_tevents_missing_timeml_core=0,
        max_timex_missing_timeml_core=0,
        max_signals_missing_text_span=0,
        max_tlinks_missing_reltype_canonical=0,
    )
    result = PhaseAssertions(graph, thresholds=thresholds).after_temporal()

    assert result.passed is False
    assert any("expected <= 0" in err for err in result.errors)
