"""Integration tests for Iteration 4 evaluation harness against live graph."""

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
    reason="Neo4j unavailable; skipping evaluation integration tests",
)


@pytest.fixture(scope="module")
def graph():
    from textgraphx.database.client import make_graph_from_config

    return make_graph_from_config()


@neo4j_required
@pytest.mark.integration
class TestEvaluationHarnessIntegration:
    def test_graph_count_snapshot_returns_non_negative_counts(self, graph):
        from textgraphx.evaluation.metrics import GraphEvaluationHarness

        h = GraphEvaluationHarness(graph)
        snapshot = h.graph_count_snapshot()

        assert snapshot["AnnotatedText"] >= 0
        assert snapshot["Sentence"] >= 0
        assert snapshot["TagOccurrence"] >= 0
        assert snapshot["TEvent"] >= 0
        assert snapshot["TIMEX"] >= 0
        assert snapshot["TLINK"] >= 0

    def test_temporal_coverage_report_shape(self, graph):
        from textgraphx.evaluation.metrics import GraphEvaluationHarness

        h = GraphEvaluationHarness(graph)
        report = h.temporal_coverage_report()

        assert report["dimension"] == "temporal"
        assert "metrics" in report
        assert "coverage" in report
        assert report["coverage"]["coverage"] >= 0.0

    def test_entity_coverage_report_shape(self, graph):
        from textgraphx.evaluation.metrics import GraphEvaluationHarness

        h = GraphEvaluationHarness(graph)
        report = h.entity_coverage_report()

        assert report["dimension"] == "entity"
        assert "metrics" in report
        assert "coverage" in report
        assert report["coverage"]["coverage"] >= 0.0
