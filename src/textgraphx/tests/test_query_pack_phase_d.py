"""Phase-D query pack tests for TLINK consistency and family diagnostics."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_phase_d_tlink_diagnostics():
    from textgraphx.queries.query_pack import available_queries

    names = available_queries()
    assert "tlink_consistency_violations" in names
    assert "tlink_family_distribution" in names
    assert "tlink_suppression_inventory" in names
    assert "tlink_anchor_consistency_inventory" in names


@pytest.mark.unit
def test_tlink_consistency_violations_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("tlink_consistency_violations")
    assert "MATCH (a)-[r1:TLINK]->(b), (a)-[r2:TLINK]->(b)" in q
    assert "conflict_count" in q


@pytest.mark.unit
def test_tlink_family_distribution_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("tlink_family_distribution")
    assert "evidence_source" in q
    assert "rule_id" in q
    assert "suppressed" in q


@pytest.mark.unit
def test_tlink_anchor_consistency_inventory_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("tlink_anchor_consistency_inventory")
    assert "MATCH ()-[r:TLINK]->()" in q
    assert "anchorConsistency" in q
    assert "anchorConsistencyReason" in q
    assert "tlink_anchor_consistency_filter" in q
