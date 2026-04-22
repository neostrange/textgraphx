"""Phase-0 unit tests for provenance contract checks in phase assertions."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_temporal_provenance_contract_fails_when_missing_fields():
    from textgraphx.phase_assertions import PhaseAssertions

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    with patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance", return_value=2):
        result = PhaseAssertions(graph, enforce_provenance_contracts=True).after_temporal()

    assert result.passed is False
    assert any("missing provenance contract fields" in c["label"] for c in result.checks)


@pytest.mark.unit
def test_event_enrichment_provenance_contract_passes_when_complete():
    from textgraphx.phase_assertions import PhaseAssertions

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    with patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance", return_value=0):
        result = PhaseAssertions(graph, enforce_provenance_contracts=True).after_event_enrichment()

    assert result.passed is True
    labels = [c["label"] for c in result.checks]
    assert "DESCRIBES relationships missing provenance contract fields" in labels
    assert "EVENT_PARTICIPANT relationships missing provenance contract fields" in labels


@pytest.mark.unit
def test_tlinks_provenance_contract_runs_when_enabled():
    from textgraphx.phase_assertions import PhaseAssertions

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    with patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance", return_value=0):
        result = PhaseAssertions(graph, enforce_provenance_contracts=True).after_tlinks()

    assert result.passed is True
    assert any("TLINK relationships missing provenance contract fields" in c["label"] for c in result.checks)
