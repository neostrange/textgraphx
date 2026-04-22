"""Unit tests for textgraphx/phase_assertions.py.

All tests use a mock graph so no real Neo4j connection is required.
"""

import pytest
from unittest.mock import MagicMock, call, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.phase_assertions import (
    AssertionResult,
    PhaseAssertions,
    PhaseThresholds,
    record_phase_run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(count: int = 5) -> MagicMock:
    """Return a mock graph whose .run().data() always returns [{'c': count}]."""
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": count}]
    return graph


# ---------------------------------------------------------------------------
# AssertionResult unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAssertionResult:
    def test_initial_state_is_passing(self):
        result = AssertionResult(phase="test", passed=True)
        assert result.passed is True
        assert result.checks == []
        assert result.errors == []

    def test_add_check_passes_when_actual_meets_minimum(self):
        result = AssertionResult(phase="ingestion", passed=True)
        result.add_check("nodes", actual=10, minimum=5)
        assert result.passed is True
        assert result.checks[0]["passed"] is True
        assert result.errors == []

    def test_add_check_fails_when_below_minimum(self):
        result = AssertionResult(phase="ingestion", passed=True)
        result.add_check("nodes", actual=3, minimum=5)
        assert result.passed is False
        assert result.checks[0]["passed"] is False
        assert len(result.errors) == 1
        assert "got 3, expected >= 5" in result.errors[0]

    def test_multiple_checks_one_failure_marks_result_failed(self):
        result = AssertionResult(phase="ingestion", passed=True)
        result.add_check("A", actual=10, minimum=1)   # passes
        result.add_check("B", actual=0, minimum=1)    # fails
        assert result.passed is False
        assert len(result.errors) == 1

    def test_add_check_exact_minimum_passes(self):
        result = AssertionResult(phase="x", passed=True)
        result.add_check("exactly minimum", actual=5, minimum=5)
        assert result.passed is True

    def test_log_summary_does_not_raise(self):
        result = AssertionResult(phase="ingestion", passed=True)
        result.add_check("nodes", actual=10, minimum=5)
        result.log_summary()  # should not raise


# ---------------------------------------------------------------------------
# PhaseThresholds unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhaseThresholds:
    def test_defaults_are_permissive(self):
        t = PhaseThresholds()
        assert t.min_annotated_text == 1
        assert t.min_sentences == 1
        assert t.min_tag_occurrences == 10
        assert t.min_tevents == 0
        assert t.min_tlink_rels == 0

    def test_custom_thresholds(self):
        t = PhaseThresholds(
            min_tevents=5,
            min_tlink_rels=3,
            min_signals=2,
            min_frame_describes_event_rels=2,
            min_has_frame_argument_rels=2,
            min_event_participant_rels=2,
            min_clink_rels=1,
            min_slink_rels=1,
        )
        assert t.min_tevents == 5
        assert t.min_tlink_rels == 3
        assert t.min_signals == 2
        assert t.min_frame_describes_event_rels == 2
        assert t.min_has_frame_argument_rels == 2
        assert t.min_event_participant_rels == 2
        assert t.min_clink_rels == 1
        assert t.min_slink_rels == 1


# ---------------------------------------------------------------------------
# PhaseAssertions unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhaseAssertions:
    def test_after_ingestion_passes_with_data(self):
        graph = _make_graph(count=20)
        pa = PhaseAssertions(graph)
        result = pa.after_ingestion()
        assert result.passed is True
        assert result.phase == "ingestion"
        assert len(result.checks) == 3  # AnnotatedText, Sentence, TagOccurrence

    def test_after_ingestion_fails_when_counts_zero(self):
        graph = _make_graph(count=0)
        t = PhaseThresholds(min_annotated_text=1, min_sentences=1, min_tag_occurrences=10)
        pa = PhaseAssertions(graph, thresholds=t)
        result = pa.after_ingestion()
        assert result.passed is False
        assert len(result.errors) == 3  # all three checks should fail

    def test_after_refinement_passes_with_zero_thresholds(self):
        graph = _make_graph(count=0)
        t = PhaseThresholds(
            min_named_entities_with_head=0,
            min_refers_to_rels=0,
            min_nominal_semantic_heads=0,
        )
        pa = PhaseAssertions(graph, thresholds=t)
        result = pa.after_refinement()
        assert result.passed is True

    def test_after_refinement_includes_nominal_semantic_head_check(self):
        graph = _make_graph(count=4)
        pa = PhaseAssertions(graph)
        result = pa.after_refinement()
        labels = [c["label"] for c in result.checks]
        assert "EntityMention nodes with nominal semantic head" in labels
        assert "Endpoint contract violations (REFERS_TO)" in labels
        assert "Endpoint contract violations (HAS_LEMMA)" in labels
        assert "EntityMention nodes missing REFERS_TO->Entity" in labels
        assert "NamedEntity nodes missing token identity fields" in labels
        assert "EntityMention nodes missing doc/span identity fields" in labels

    def test_after_temporal_returns_expected_checks(self):
        graph = _make_graph(count=3)
        pa = PhaseAssertions(graph)
        result = pa.after_temporal()
        assert result.phase == "temporal"
        labels = [c["label"] for c in result.checks]
        assert "TEvent nodes" in labels
        assert "TIMEX nodes" in labels
        assert "Signal nodes" in labels
        assert "TEvent nodes missing core TimeML fields" in labels
        assert "TIMEX nodes missing core TimeML fields" in labels
        assert "Signal nodes missing text/span fields" in labels
        assert "TLINK relationships missing relTypeCanonical" in labels

    def test_after_event_enrichment_checks_correct_labels(self):
        graph = _make_graph(count=5)
        pa = PhaseAssertions(graph)
        result = pa.after_event_enrichment()
        labels = [c["label"] for c in result.checks]
        assert "DESCRIBES relationships (Frame->TEvent)" in labels
        assert "PARTICIPANT relationships" in labels
        assert "FRAME_DESCRIBES_EVENT relationships" in labels
        assert "HAS_FRAME_ARGUMENT relationships" in labels
        assert "EVENT_PARTICIPANT relationships" in labels
        assert "Telemetry: Frame->TEvent canonical minus legacy" in labels
        assert "Telemetry: Participant canonical minus legacy" in labels
        assert "Cost-model: EVENT_PARTICIPANT per described event" in labels
        assert "Cost-model: HAS_FRAME_ARGUMENT per described event" in labels
        assert "CLINK relationships" in labels
        assert "SLINK relationships" in labels
        assert "Endpoint contract violations (MODIFIES)" in labels
        assert "Endpoint contract violations (AFFECTS)" in labels
        assert "Endpoint contract violations (CLINK)" in labels
        assert "Endpoint contract violations (SLINK)" in labels
        assert "EventMention nodes missing REFERS_TO->TEvent" in labels
        assert "Frame nodes with described events missing INSTANTIATES->EventMention" in labels
        assert "EventMention nodes missing token identity fields" in labels
        assert "EventMention nodes missing factuality" in labels
        assert "EventMention factuality records missing attribution" in labels
        assert "TEvent nodes missing factuality after mention sync" in labels
        assert "EventMention/TEvent factuality alignment violations" in labels
        assert "TagOccurrence links missing IN_FRAME alias" in labels
        assert "TagOccurrence links missing IN_MENTION alias" in labels

    def test_after_refinement_identity_and_chain_checks_fail_when_thresholds_zero(self):
        graph = _make_graph(count=1)
        thresholds = PhaseThresholds(
            max_entity_mentions_missing_refers_to_entity=0,
            max_named_entities_missing_token_identity=0,
            max_entity_mentions_missing_identity_fields=0,
        )
        pa = PhaseAssertions(graph, thresholds=thresholds)

        result = pa.after_refinement()
        assert result.passed is False
        assert any("missing REFERS_TO->Entity" in e for e in result.errors)

    def test_after_event_enrichment_chain_and_identity_checks_fail_when_thresholds_zero(self):
        graph = _make_graph(count=1)
        thresholds = PhaseThresholds(
            max_event_mentions_missing_refers_to_tevent=0,
            max_frames_missing_instantiates_eventmention=0,
            max_event_mentions_missing_token_identity=0,
            max_participation_in_frame_missing=0,
            max_participation_in_mention_missing=0,
        )
        pa = PhaseAssertions(graph, thresholds=thresholds)

        result = pa.after_event_enrichment()
        assert result.passed is False
        assert any("missing REFERS_TO->TEvent" in e for e in result.errors)

    def test_after_tlinks_checks_tlink_relationships(self):
        graph = _make_graph(count=7)
        pa = PhaseAssertions(graph)
        result = pa.after_tlinks()
        assert result.checks[0]["label"] == "TLINK relationships"
        assert result.checks[0]["actual"] == 7
        labels = [c["label"] for c in result.checks]
        assert "Cost-model: TLINK relationships upper bound" in labels

    def test_hard_fail_raises_assertion_error(self):
        graph = _make_graph(count=0)
        t = PhaseThresholds(min_annotated_text=1)
        pa = PhaseAssertions(graph, thresholds=t, hard_fail=True)
        with pytest.raises(AssertionError, match="ingestion"):
            pa.after_ingestion()

    def test_hard_fail_false_does_not_raise(self):
        graph = _make_graph(count=0)
        t = PhaseThresholds(min_annotated_text=1)
        pa = PhaseAssertions(graph, thresholds=t, hard_fail=False)
        result = pa.after_ingestion()  # should not raise
        assert result.passed is False

    def test_graph_run_exception_propagates(self):
        graph = MagicMock()
        graph.run.side_effect = RuntimeError("db down")
        pa = PhaseAssertions(graph)
        with pytest.raises(RuntimeError):
            pa.after_ingestion()

    def test_count_returns_zero_on_empty_data(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        pa = PhaseAssertions(graph)
        # after_temporal thresholds default to 0 so it should pass
        result = pa.after_temporal()
        assert result.passed is True
        assert all(c["actual"] == 0 for c in result.checks)

    def test_strict_transition_gate_fails_when_legacy_edges_dominate(self):
        graph = MagicMock()
        graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"c": 5}])),  # DESCRIBES
            MagicMock(data=MagicMock(return_value=[{"c": 2}])),  # FRAME_DESCRIBES_EVENT
            MagicMock(data=MagicMock(return_value=[{"c": 6}])),  # PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 3}])),  # EVENT_PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # HAS_FRAME_ARGUMENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # CLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # SLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint EVENT_PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint INSTANTIATES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint HAS_FRAME_ARGUMENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint FRAME_DESCRIBES_EVENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint REFERS_TO
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint MODIFIES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint AFFECTS
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint CLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint SLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # EventMention missing REFERS_TO
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # Frame missing INSTANTIATES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # EventMention missing token identity
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality missing on EventMention
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality attribution missing
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality missing on TEvent
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality alignment violations
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # participation IN_FRAME alias missing
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # participation IN_MENTION alias missing
        ]
        pa = PhaseAssertions(graph, strict_transition_gate=True)
        result = pa.after_event_enrichment()
        assert result.passed is False
        assert any("strict transition gate failed" in err for err in result.errors)

    def test_strict_transition_gate_passes_when_canonical_edges_dominate(self):
        graph = MagicMock()
        graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"c": 1}])),  # DESCRIBES
            MagicMock(data=MagicMock(return_value=[{"c": 3}])),  # FRAME_DESCRIBES_EVENT
            MagicMock(data=MagicMock(return_value=[{"c": 1}])),  # PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 4}])),  # EVENT_PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # HAS_FRAME_ARGUMENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # CLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # SLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint EVENT_PARTICIPANT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint INSTANTIATES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint HAS_FRAME_ARGUMENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint FRAME_DESCRIBES_EVENT
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint REFERS_TO
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint MODIFIES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint AFFECTS
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint CLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # endpoint SLINK
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # EventMention missing REFERS_TO
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # Frame missing INSTANTIATES
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # EventMention missing token identity
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality missing on EventMention
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality attribution missing
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality missing on TEvent
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # factuality alignment violations
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # participation IN_FRAME alias missing
            MagicMock(data=MagicMock(return_value=[{"c": 0}])),  # participation IN_MENTION alias missing
        ]
        pa = PhaseAssertions(graph, strict_transition_gate=True)
        result = pa.after_event_enrichment()
        assert result.passed is True

    def test_event_enrichment_factuality_quality_gate_fails_when_thresholds_zero(self):
        graph = _make_graph(count=1)
        thresholds = PhaseThresholds(
            max_event_mentions_missing_factuality=0,
            max_event_mentions_missing_factuality_attribution=0,
            max_tevents_missing_factuality=0,
            max_factuality_alignment_violations=0,
        )
        pa = PhaseAssertions(graph, thresholds=thresholds)

        result = pa.after_event_enrichment()
        assert result.passed is False
        assert any("missing factuality" in e for e in result.errors)

    @patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance")
    def test_temporal_provenance_contract_fails_when_missing_fields(self, mocked_validate):
        graph = _make_graph(count=1)
        mocked_validate.return_value = 2
        pa = PhaseAssertions(graph, enforce_provenance_contracts=True)

        result = pa.after_temporal()
        assert result.passed is False
        assert any("missing provenance contract fields" in c["label"] for c in result.checks)

    @patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance")
    def test_event_enrichment_provenance_contract_passes_when_complete(self, mocked_validate):
        graph = _make_graph(count=1)
        mocked_validate.return_value = 0
        pa = PhaseAssertions(graph, enforce_provenance_contracts=True)

        result = pa.after_event_enrichment()
        assert result.passed is True
        labels = [c["label"] for c in result.checks]
        assert "DESCRIBES relationships missing provenance contract fields" in labels
        assert "EVENT_PARTICIPANT relationships missing provenance contract fields" in labels
        assert "MODIFIES relationships missing provenance contract fields" in labels
        assert "AFFECTS relationships missing provenance contract fields" in labels

    def test_event_enrichment_cost_model_fails_when_density_too_high(self):
        graph = _make_graph(count=10)
        thresholds = PhaseThresholds(
            max_event_participants_per_described_event=0.1,
            max_frame_arguments_per_described_event=0.1,
        )
        pa = PhaseAssertions(graph, thresholds=thresholds)

        result = pa.after_event_enrichment()
        assert result.passed is False
        assert any("Cost-model" in e for e in result.errors)

    def test_tlinks_cost_model_upper_bound_can_fail(self):
        graph = _make_graph(count=5)
        thresholds = PhaseThresholds(min_tlink_rels=0, max_tlink_rels=3)
        pa = PhaseAssertions(graph, thresholds=thresholds)

        result = pa.after_tlinks()
        assert result.passed is False
        assert any("TLINK relationships upper bound" in e for e in result.errors)

    @patch("textgraphx.phase_assertions.validate_inferred_relationship_provenance")
    def test_tlinks_provenance_contract_runs_when_enabled(self, mocked_validate):
        graph = _make_graph(count=1)
        mocked_validate.return_value = 0
        pa = PhaseAssertions(graph, enforce_provenance_contracts=True)

        result = pa.after_tlinks()
        assert result.passed is True
        assert any("TLINK relationships missing provenance contract fields" in c["label"] for c in result.checks)


# ---------------------------------------------------------------------------
# record_phase_run unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecordPhaseRun:
    def test_writes_phase_run_node(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"node_id": 1}]
        record_phase_run(graph, "ingestion", duration_seconds=10.5, documents_processed=3)
        graph.run.assert_called_once()
        cypher_arg = graph.run.call_args[0][0]
        assert "PhaseRun" in cypher_arg
        params = graph.run.call_args[0][1]
        assert params["props"]["phase"] == "ingestion"
        assert params["props"]["documents_processed"] == 3
        assert params["props"]["duration_seconds"] == 10.5

    def test_metadata_is_prefixed_with_meta_(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(
            graph, "temporal", duration_seconds=5.0, metadata={"passes": "a,b"}
        )
        params = graph.run.call_args[0][1]
        assert "meta_passes" in params["props"]
        assert params["props"]["meta_passes"] == "a,b"

    def test_does_not_raise_when_graph_fails(self):
        graph = MagicMock()
        graph.run.side_effect = Exception("connection failed")
        # Should log but not re-raise
        record_phase_run(graph, "tlinks", duration_seconds=1.0)

    def test_duration_is_rounded(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(graph, "refinement", duration_seconds=1.23456789)
        params = graph.run.call_args[0][1]
        assert params["props"]["duration_seconds"] == 1.235
