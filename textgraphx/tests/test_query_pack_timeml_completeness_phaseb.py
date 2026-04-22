"""Phase-B tests for TimeML completeness diagnostics in query pack."""

import pytest


@pytest.mark.unit
def test_query_pack_includes_timeml_completeness_queries():
    from textgraphx.queries.query_pack import available_queries

    names = available_queries()
    assert "timeml_event_field_completeness" in names
    assert "timeml_timex_field_completeness" in names
    assert "timeml_signal_field_completeness" in names
    assert "timeml_tlink_field_completeness" in names


@pytest.mark.unit
def test_timeml_event_field_completeness_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("timeml_event_field_completeness")
    assert "MATCH (e:TEvent)" in q
    assert "missing_core" in q
    assert "with_tense" in q


@pytest.mark.unit
def test_timeml_tlink_field_completeness_query_shape():
    from textgraphx.queries.query_pack import load_query

    q = load_query("timeml_tlink_field_completeness")
    assert "MATCH ()-[r:TLINK]->()" in q
    assert "with_rel_type_canonical" in q
    assert "missing_canonical" in q
