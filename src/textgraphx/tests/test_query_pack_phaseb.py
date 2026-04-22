"""Phase-B query pack tests for TLINK inventory diagnostics."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_tlink_relation_inventory():
    from textgraphx.queries.query_pack import available_queries

    assert "tlink_relation_inventory" in available_queries()


@pytest.mark.unit
def test_load_tlink_relation_inventory_query_contains_expected_fields():
    from textgraphx.queries.query_pack import load_query

    q = load_query("tlink_relation_inventory")
    assert "MATCH ()-[r:TLINK]-()" in q
    assert "rel_type_canonical" in q
    assert "rel_count" in q
