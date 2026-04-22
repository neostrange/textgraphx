"""Phase-E query pack tests for coverage and provenance diagnostics."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_phase_e_diagnostics():
    from textgraphx.queries.query_pack import available_queries

    names = available_queries()
    assert "clause_scope_population_rate" in names
    assert "provenance_contract_breakdown" in names


@pytest.mark.unit
def test_clause_scope_population_rate_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("clause_scope_population_rate")
    assert "MATCH (d:AnnotatedText)" in q
    assert "clause_coverage" in q
    assert "scope_coverage" in q


@pytest.mark.unit
def test_provenance_contract_breakdown_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("provenance_contract_breakdown")
    assert "FRAME_DESCRIBES_EVENT" in q
    assert "total_missing_fields" in q
    assert "missing_confidence" in q
