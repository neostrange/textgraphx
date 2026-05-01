"""Contract tests for NounChunk id uniqueness.

Validates that no two NounChunk nodes in the same document share an id,
and that ids are either canonical or accepted legacy format during the
active migration window.

Live Neo4j tests; auto-skipped when the server is unreachable.
"""

import pytest

from textgraphx.database.client import make_graph_from_config


@pytest.fixture(scope="module")
def graph():
    return make_graph_from_config()


@pytest.mark.integration
@pytest.mark.contract
def test_nounchunk_id_uniqueness(graph):
    """NounChunk.id values must be globally unique."""
    query = """
        MATCH (nc:NounChunk)
        WHERE nc.id IS NOT NULL
        WITH nc.id AS nc_id, count(*) AS cnt
        WHERE cnt > 1
        RETURN nc_id, cnt
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], f"NounChunk id duplicates found: {rows}"


@pytest.mark.integration
@pytest.mark.contract
def test_nounchunk_id_has_allowed_format(graph):
    """NounChunk ids must be canonical or legacy-safe during migration window.

    Canonical format: nc_<doc>_<start>_<end>_<head>
    Legacy format tolerated temporarily: <doc>_<start>
    """
    query = """
        MATCH (nc:NounChunk)
        WHERE nc.id IS NOT NULL
          AND NOT (
            nc.id STARTS WITH 'nc_'
            OR nc.id =~ '^[^_]+_[0-9]+$'
          )
        RETURN nc.id AS id
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], (
        f"NounChunk nodes found with invalid id format (neither canonical nor legacy): {rows}"
    )


@pytest.mark.integration
@pytest.mark.contract
def test_nounchunk_span_integrity(graph):
    """NounChunk start_tok must be <= end_tok."""
    query = """
        MATCH (nc:NounChunk)
        WHERE nc.start_tok IS NOT NULL
          AND nc.end_tok   IS NOT NULL
          AND nc.start_tok > nc.end_tok
        RETURN nc.id AS id, nc.start_tok AS start, nc.end_tok AS end
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], f"NounChunk span integrity violated: {rows}"
