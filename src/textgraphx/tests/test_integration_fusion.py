"""Integration tests for Iteration 4.15 cross-sentence/cross-document fusion."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _neo4j_available() -> bool:
    try:
        from textgraphx.infrastructure.health_check import check_neo4j_connection
        from textgraphx.config import get_config

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
    reason="Neo4j unavailable; skipping fusion integration tests",
)


@pytest.fixture(scope="module")
def graph():
    from textgraphx.neo4j_client import make_graph_from_config

    return make_graph_from_config()


@neo4j_required
@pytest.mark.integration
class TestFusionIntegration:
    def test_cross_sentence_fusion_executes(self, graph):
        from textgraphx.reasoning.fusion import fuse_entities_cross_sentence

        count = fuse_entities_cross_sentence(graph)
        assert count >= 0

    def test_cross_document_fusion_executes(self, graph):
        from textgraphx.reasoning.fusion import fuse_entities_cross_document

        count = fuse_entities_cross_document(graph)
        assert count >= 0

    def test_same_as_relationships_have_provenance(self, graph):
        rows = graph.run(
            """
            MATCH ()-[r:SAME_AS]->()
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_co_occurs_with_relationships_have_provenance(self, graph):
        rows = graph.run(
            """
            MATCH ()-[r:CO_OCCURS_WITH]->()
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0
