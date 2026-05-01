"""Contract tests for NamedEntity span uniqueness per document.

Validates the hard contract: no two NamedEntity nodes in the same document
share (doc_id, start_tok, end_tok, type).

These tests require a live Neo4j instance and are auto-skipped when none is
reachable (conftest.py handles that).
"""
import pytest
from textgraphx.database.client import make_graph_from_config


@pytest.fixture(scope="module")
def graph():
    return make_graph_from_config()


@pytest.mark.integration
@pytest.mark.contract
def test_named_entity_span_uniqueness_per_doc(graph):
    """No two NamedEntity nodes may share (doc_id, start_tok, end_tok, type)
    within the same document.

    Duplicates here indicate EntityFuser or ingestion wrote conflicting nodes
    without deduplication, which undermines mention-level F1 computation.
    """
    query = """
        MATCH (ne:NamedEntity)
        WHERE ne.start_tok IS NOT NULL
          AND ne.end_tok   IS NOT NULL
          AND ne.type      IS NOT NULL
        WITH coalesce(ne.document_id, split(ne.id, '_')[0]) AS doc_id,
             ne.start_tok AS start,
             ne.end_tok   AS end,
             ne.type      AS type,
             count(ne)    AS cnt
        WHERE cnt > 1
        RETURN doc_id, start, end, type, cnt
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], (
        f"Found NamedEntity span duplicates (doc_id, start_tok, end_tok, type): {rows[:5]}"
    )


@pytest.mark.integration
@pytest.mark.contract
def test_entity_mention_uid_uniqueness(graph):
    """EntityMention.uid must be unique across the graph.

    Duplicates indicate the uid-generation or MERGE logic is broken.
    """
    query = """
        MATCH (em:EntityMention)
        WHERE em.uid IS NOT NULL
        WITH em.uid AS uid, count(*) AS cnt
        WHERE cnt > 1
        RETURN uid, cnt
        LIMIT 5
    """
    rows = graph.run(query).data()
    assert rows == [], f"EntityMention uid duplicates found: {rows}"


@pytest.mark.integration
@pytest.mark.contract
def test_span_integrity_start_lte_end(graph):
    """start_tok must be <= end_tok on all span-bearing nodes.

    Violation breaks MEANTIME boundary alignment.
    """
    query = """
        CALL {
            MATCH (n:NamedEntity) WHERE n.start_tok > n.end_tok RETURN labels(n) AS lbl, n.id AS nid
            UNION ALL
            MATCH (n:EntityMention) WHERE n.start_tok > n.end_tok RETURN labels(n) AS lbl, n.id AS nid
            UNION ALL
            MATCH (n:CorefMention) WHERE n.start_tok > n.end_tok RETURN labels(n) AS lbl, n.id AS nid
            UNION ALL
            MATCH (n:NounChunk) WHERE n.start_tok > n.end_tok RETURN labels(n) AS lbl, n.id AS nid
        }
        RETURN lbl, nid LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], f"Span integrity violated (start_tok > end_tok): {rows}"
