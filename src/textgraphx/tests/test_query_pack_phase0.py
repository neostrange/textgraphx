"""Phase-0 query pack regression tests."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_provenance_contract_violations():
    from textgraphx.queries.query_pack import available_queries

    names = available_queries()
    assert "provenance_contract_violations" in names


@pytest.mark.unit
def test_query_pack_loads_provenance_contract_violations_query():
    from textgraphx.queries.query_pack import load_query

    q = load_query("provenance_contract_violations")
    assert "missing_contract_count" in q
    assert "authority_tier" in q
    assert "conflict_policy" in q
