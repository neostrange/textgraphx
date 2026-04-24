"""Integration tests for Iteration 3 cross-phase invariants.

These tests use the stable query pack and validate graph-level invariants
across multiple phases.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _neo4j_available() -> bool:
    try:
        from textgraphx.infrastructure.health_check import check_neo4j_connection
        from textgraphx.infrastructure.config import get_config
        cfg = get_config()
        ok, _ = check_neo4j_connection(
            uri=cfg.neo4j.uri,
            user=cfg.neo4j.user,
            password=cfg.neo4j.password,
        )
        return ok
    except Exception:
        return False


neo4j_required = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j not reachable — skipping cross-phase integration tests",
)


@pytest.fixture(scope="module")
def graph():
    from textgraphx.database.client import make_graph_from_config
    return make_graph_from_config()


@neo4j_required
@pytest.mark.integration
class TestQueryPackExecution:
    def test_counts_by_label_query_executes(self, graph):
        from textgraphx.queries.query_pack import load_query
        q = load_query("counts_by_label")
        rows = graph.run(q).data()
        assert isinstance(rows, list)

    def test_recent_phase_runs_query_executes(self, graph):
        from textgraphx.queries.query_pack import load_query
        q = load_query("recent_phase_runs")
        rows = graph.run(q).data()
        assert isinstance(rows, list)

    def test_doc_invariants_query_executes(self, graph):
        from textgraphx.queries.query_pack import load_query
        q = load_query("doc_invariants")
        rows = graph.run(q).data()
        assert isinstance(rows, list)


@neo4j_required
@pytest.mark.integration
@pytest.mark.slow
class TestCrossPhaseInvariants:
    def test_docs_have_non_negative_counts(self, graph):
        from textgraphx.queries.query_pack import load_query
        rows = graph.run(load_query("doc_invariants")).data()
        for row in rows:
            assert row["sentence_count"] >= 0
            assert row["token_count"] >= 0
            assert row["tevent_count"] >= 0
            assert row["timex_count"] >= 0

    def test_temporal_nodes_imply_tokens(self, graph):
        from textgraphx.queries.query_pack import load_query
        rows = graph.run(load_query("doc_invariants")).data()
        for row in rows:
            if row["tevent_count"] > 0 or row["timex_count"] > 0:
                assert row["token_count"] > 0

    def test_tlink_edges_have_valid_endpoints(self, graph):
        rows = graph.run(
            """
            MATCH (a)-[r:TLINK]->(b)
            WHERE NOT ((a:TEvent OR a:TIMEX) AND (b:TEvent OR b:TIMEX))
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_event_description_edges_have_valid_endpoints(self, graph):
        rows = graph.run(
            """
            MATCH (a)-[r:FRAME_DESCRIBES_EVENT|DESCRIBES]->(b)
            WHERE a:Frame AND NOT b:TEvent
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_phase_run_markers_have_required_properties(self, graph):
        rows = graph.run(
            """
            MATCH (r:PhaseRun)
            WHERE r.phase IS NULL OR r.timestamp IS NULL OR r.duration_seconds IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_non_fusion_edges_do_not_cross_document_ids(self, graph):
        rows = graph.run(
            """
            MATCH (a)-[r]->(b)
                        WHERE type(r) IN [
                                'TLINK',
                                'DESCRIBES',
                                'FRAME_DESCRIBES_EVENT',
                                'TRIGGERS',
                                'PARTICIPANT',
                                'EVENT_PARTICIPANT',
                                'INSTANTIATES',
                                'CLINK',
                                'SLINK'
                        ]
              AND a.doc_id IS NOT NULL
              AND b.doc_id IS NOT NULL
              AND toString(a.doc_id) <> toString(b.doc_id)
            RETURN type(r) AS rel_type, count(r) AS c
            ORDER BY c DESC
            """
        ).data()
        assert rows == []
