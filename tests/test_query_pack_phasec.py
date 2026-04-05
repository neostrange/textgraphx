"""Phase-C query pack tests for clause/scope diagnostics."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_clause_scope_inventory():
    from textgraphx.queries.query_pack import available_queries

    assert "clause_scope_inventory" in available_queries()


@pytest.mark.unit
def test_clause_scope_inventory_query_has_expected_fields():
    from textgraphx.queries.query_pack import load_query

    q = load_query("clause_scope_inventory")
    assert "MATCH (em:EventMention)" in q
    assert "clause_type" in q
    assert "scope_type" in q
