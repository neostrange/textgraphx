"""Phase-C regression tests for clause/scope enrichment contract."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_event_enrichment_contains_clause_scope_query_contract():
    src = (Path(__file__).parent.parent / "EventEnrichmentPhase.py").read_text(encoding="utf-8")

    assert "query_clause_scope" in src
    assert "em.clauseType" in src
    assert "em.scopeType" in src
    assert "em.temporalCueHeads" in src
    assert "event_enrichment_clause_scope" in src


@pytest.mark.unit
def test_clause_scope_temporal_cue_inventory_includes_core_connectives():
    src = (Path(__file__).parent.parent / "EventEnrichmentPhase.py").read_text(encoding="utf-8")

    for cue in ["before", "after", "since", "until", "during", "while", "when", "if", "because", "although"]:
        assert f"'{cue}'" in src
