"""Integration tests for provenance/confidence attributes on inferred links."""

import pytest
import sys
from pathlib import Path
from uuid import uuid4

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
    reason="Neo4j unavailable; skipping provenance integration tests",
)


@pytest.fixture(scope="module")
def graph():
    from textgraphx.neo4j_client import make_graph_from_config

    return make_graph_from_config()


@neo4j_required
@pytest.mark.integration
class TestProvenanceIntegration:
    def test_stamp_tlink_provenance(self, graph):
        from textgraphx.provenance import stamp_inferred_relationships

        stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.75,
            evidence_source="tlinks_recognizer",
            rule_id="integration_stamp",
        )

        rows = graph.run(
            """
            MATCH ()-[r:TLINK]->()
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_stamp_describes_provenance(self, graph):
        from textgraphx.provenance import stamp_inferred_relationships

        stamp_inferred_relationships(
            graph,
            rel_type="DESCRIBES",
            confidence=0.7,
            evidence_source="event_enrichment",
            rule_id="integration_stamp",
        )

        rows = graph.run(
            """
            MATCH (f:Frame)-[r:DESCRIBES]->(t:TEvent)
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_stamp_frame_describes_event_provenance(self, graph):
        from textgraphx.provenance import stamp_inferred_relationships

        stamp_inferred_relationships(
            graph,
            rel_type="FRAME_DESCRIBES_EVENT",
            confidence=0.7,
            evidence_source="event_enrichment",
            rule_id="integration_stamp",
        )

        rows = graph.run(
            """
            MATCH ()-[r:FRAME_DESCRIBES_EVENT]->()
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_keyword_document_never_uses_describes_edge(self, graph):
        """Ensure Keyword -[:DESCRIBES]-> AnnotatedText edges do not exist.
        
        Keywords link to documents via KEYWORD_DESCRIBES_DOCUMENT, not DESCRIBES,
        to keep DESCRIBES semantically pure (Frame-TEvent event description only).
        This test prevents accidental regression to the old overloaded design.
        """
        rows = graph.run(
            """
            MATCH (kw:Keyword)-[r:DESCRIBES]->(doc:AnnotatedText)
            RETURN count(r) AS bad_count
            """
        ).data()
        assert rows[0]["bad_count"] == 0, \
            "Found Keyword -[:DESCRIBES]-> AnnotatedText edges; use KEYWORD_DESCRIBES_DOCUMENT instead"

    def test_stamp_event_participant_provenance(self, graph):
        from textgraphx.provenance import stamp_inferred_relationships

        stamp_inferred_relationships(
            graph,
            rel_type="EVENT_PARTICIPANT",
            confidence=0.65,
            evidence_source="event_enrichment",
            rule_id="integration_stamp",
        )

        rows = graph.run(
            """
            MATCH ()-[r:EVENT_PARTICIPANT]->()
            WHERE r.confidence IS NULL OR r.evidence_source IS NULL OR r.rule_id IS NULL
            RETURN count(r) AS bad
            """
        ).data()
        assert rows[0]["bad"] == 0

    def test_tlink_preserve_existing_blocks_case_rule_collapse(self, graph):
        """Case-level TLINK provenance must survive global TLINK backfill stamping."""
        from textgraphx.provenance import stamp_inferred_relationships

        probe_id = f"tlink_prov_{uuid4().hex}"
        graph.run(
            """
            CREATE (a:TgxProvenanceProbe {probe_id: $probe_id, name: 'a'})
            CREATE (b:TgxProvenanceProbe {probe_id: $probe_id, name: 'b'})
            CREATE (c:TgxProvenanceProbe {probe_id: $probe_id, name: 'c'})
            CREATE (d:TgxProvenanceProbe {probe_id: $probe_id, name: 'd'})
            CREATE (e:TgxProvenanceProbe {probe_id: $probe_id, name: 'e'})
            CREATE (f:TgxProvenanceProbe {probe_id: $probe_id, name: 'f'})
            CREATE (a)-[:TLINK {
                probe_id: $probe_id,
                rule_id: 'case4_timex_head_match',
                confidence: 0.88,
                evidence_source: 'tlinks_recognizer'
            }]->(b)
            CREATE (c)-[:TLINK {
                probe_id: $probe_id,
                rule_id: 'case5_timex_preposition',
                confidence: 0.72,
                evidence_source: 'tlinks_recognizer'
            }]->(d)
            CREATE (e)-[:TLINK {
                probe_id: $probe_id
            }]->(f)
            """,
            {"probe_id": probe_id},
        )

        try:
            stamp_inferred_relationships(
                graph,
                rel_type="TLINK",
                confidence=0.8,
                evidence_source="tlinks_recognizer",
                rule_id="case_rules",
                preserve_existing=True,
            )

            rows = graph.run(
                """
                MATCH (:TgxProvenanceProbe {probe_id: $probe_id})-[r:TLINK {probe_id: $probe_id}]->(:TgxProvenanceProbe {probe_id: $probe_id})
                RETURN r.rule_id AS rule_id, r.confidence AS confidence, r.evidence_source AS evidence_source
                ORDER BY rule_id ASC
                """,
                {"probe_id": probe_id},
            ).data()

            assert len(rows) == 3
            by_rule = {row["rule_id"]: row for row in rows}

            assert "case4_timex_head_match" in by_rule
            assert "case5_timex_preposition" in by_rule
            assert "case_rules" in by_rule

            assert float(by_rule["case4_timex_head_match"]["confidence"]) == pytest.approx(0.88)
            assert float(by_rule["case5_timex_preposition"]["confidence"]) == pytest.approx(0.72)
            assert float(by_rule["case_rules"]["confidence"]) == pytest.approx(0.8)

            assert by_rule["case4_timex_head_match"]["evidence_source"] == "tlinks_recognizer"
            assert by_rule["case5_timex_preposition"]["evidence_source"] == "tlinks_recognizer"
            assert by_rule["case_rules"]["evidence_source"] == "tlinks_recognizer"
        finally:
            graph.run(
                """
                MATCH (n:TgxProvenanceProbe {probe_id: $probe_id})
                DETACH DELETE n
                """,
                {"probe_id": probe_id},
            )
