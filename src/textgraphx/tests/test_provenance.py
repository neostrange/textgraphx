"""Unit and regression tests for inferred-link provenance stamping."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
class TestProvenanceStamping:
    def test_stamp_relationships_executes_query(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 3}]

        count = stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.8,
            evidence_source="tlinks_recognizer",
            rule_id="case_set",
        )

        assert count == 3
        graph.run.assert_called_once()

    def test_stamp_relationships_uses_expected_params(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 0}]

        stamp_inferred_relationships(
            graph,
            rel_type="DESCRIBES",
            confidence=0.7,
            evidence_source="event_enrichment",
            rule_id="link_frame_to_event",
        )

        params = graph.run.call_args[0][1]
        assert params["confidence"] == 0.7
        assert params["source"] == "event_enrichment"
        assert params["rule_id"] == "link_frame_to_event"
        assert params["authority_tier"] == "secondary"
        assert params["source_kind"] == "rule"
        assert params["conflict_policy"] == "additive"

    def test_stamp_relationships_invalid_confidence_raises(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        with pytest.raises(ValueError):
            stamp_inferred_relationships(
                graph,
                rel_type="PARTICIPANT",
                confidence=1.1,
                evidence_source="event_enrichment",
                rule_id="bad",
            )

    def test_stamp_event_participant_uses_expected_params(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 0}]

        stamp_inferred_relationships(
            graph,
            rel_type="EVENT_PARTICIPANT",
            confidence=0.65,
            evidence_source="event_enrichment",
            rule_id="participant_linking",
        )

        params = graph.run.call_args[0][1]
        assert params["confidence"] == 0.65
        assert params["source"] == "event_enrichment"
        assert params["rule_id"] == "participant_linking"

    def test_stamp_relationships_accepts_explicit_authority_and_extra_properties(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 2}]

        count = stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.8,
            evidence_source="tlinks_recognizer",
            rule_id="case_rules",
            authority_tier="primary",
            source_kind="service",
            conflict_policy="merge",
            extra_properties={"notes": "validated"},
        )

        assert count == 2
        params = graph.run.call_args[0][1]
        assert params["authority_tier"] == "primary"
        assert params["source_kind"] == "service"
        assert params["conflict_policy"] == "merge"
        assert params["meta_notes"] == "validated"

    def test_stamp_relationships_can_preserve_existing_values(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 2}]

        stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.8,
            evidence_source="tlinks_recognizer",
            rule_id="case_rules",
            preserve_existing=True,
        )

        query = graph.run.call_args[0][0]
        assert "r.rule_id = coalesce(r.rule_id, $rule_id)" in query
        assert "r.confidence = coalesce(r.confidence, $confidence)" in query
        assert "r.evidence_source = coalesce(r.evidence_source, $source)" in query

    def test_stamp_relationships_accepts_calibration_metadata(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]

        stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.73,
            evidence_source="tlinks_recognizer",
            rule_id="case_rules",
            calibration_version="v1.0.0",
            confidence_components={"syntax": 0.8, "temporal": 0.7},
        )

        params = graph.run.call_args[0][1]
        assert params["calibration_version"] == "v1.0.0"
        assert params["confidence_components"]["syntax"] == 0.8

    def test_stamp_relationships_invalid_source_kind_raises(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        with pytest.raises(ValueError):
            stamp_inferred_relationships(
                graph,
                rel_type="PARTICIPANT",
                confidence=0.5,
                evidence_source="event_enrichment",
                rule_id="participant_linking",
                source_kind="unknown_kind",
            )

    def test_stamp_relationships_invalid_conflict_policy_raises(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        with pytest.raises(ValueError):
            stamp_inferred_relationships(
                graph,
                rel_type="PARTICIPANT",
                confidence=0.5,
                evidence_source="event_enrichment",
                rule_id="participant_linking",
                conflict_policy="unknown_policy",
            )

    def test_stamp_relationships_empty_source_raises(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        with pytest.raises(ValueError):
            stamp_inferred_relationships(
                graph,
                rel_type="PARTICIPANT",
                confidence=0.5,
                evidence_source="",
                rule_id="participant_linking",
            )


@pytest.mark.regression
class TestProvenanceContract:
    def test_stamp_relationships_returns_int(self):
        from textgraphx.provenance import stamp_inferred_relationships

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 5}]

        result = stamp_inferred_relationships(
            graph,
            rel_type="PARTICIPANT",
            confidence=0.6,
            evidence_source="event_enrichment",
            rule_id="participants",
        )

        assert isinstance(result, int)

    def test_validate_inferred_relationship_provenance_returns_int(self):
        from textgraphx.provenance import validate_inferred_relationship_provenance

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 4}]

        result = validate_inferred_relationship_provenance(graph, rel_type="TLINK")
        assert isinstance(result, int)
        assert result == 4
