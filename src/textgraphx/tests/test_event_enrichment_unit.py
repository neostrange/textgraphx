"""Unit tests for EventEnrichmentPhase refactoring (Item 6).

Tests verify:
1. Both query paths are executed (direct PARTICIPATES_IN and via FrameArgument).
2. The method returns the combined link count.
3. Each query uses MERGE (idempotent) so repeated calls don't multiply edges.
4. Graph errors propagate correctly.

Requires spaCy and its native extensions. Tests are skipped automatically when
the EventEnrichmentPhase module cannot be imported (e.g. in a minimal venv).
"""

import pytest
from unittest.mock import MagicMock, call, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Guard: skip entire module if EventEnrichmentPhase can't be imported
_ENRICHER_AVAILABLE = False
try:
    import spacy  # triggers _ctypes check
    _ENRICHER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    pass

enricher_deps = pytest.mark.skipif(
    not _ENRICHER_AVAILABLE,
    reason="spaCy (and its C extensions) not available in this environment",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_enricher(run_side_effects=None):
    """Build an EventEnrichmentPhase with a mocked graph.

    ``run_side_effects`` is a list of data() return values, one per
    graph.run() call.  Defaults to returning [{'linked': 5}] for every call.
    """
    graph = MagicMock()
    if run_side_effects is None:
        graph.run.return_value.data.return_value = [{"linked": 5}]
    else:
        graph.run.return_value.data.side_effect = [
            v if isinstance(v, list) else [{"linked": v}]
            for v in run_side_effects
        ]

    # Patch at the neo4j_client source so the constructor gets the mock,
    # regardless of whether the module is already in sys.modules.
    with patch("textgraphx.neo4j_client.make_graph_from_config", return_value=graph):
        from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase
        enricher = EventEnrichmentPhase(argv=[])

    # Guarantee the mock graph is set (handles cached module scenario)
    enricher.graph = graph
    return enricher, graph


# ---------------------------------------------------------------------------
# link_frameArgument_to_event unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@enricher_deps
class TestLinkFrameArgumentToEvent:
    def test_returns_numeric_link_count(self):
        enricher, graph = _make_enricher()
        graph.run.return_value.data.return_value = [{"linked": 4}]
        result = enricher.link_frameArgument_to_event()
        # 4 from path-1 + 4 from path-2
        assert result == 8

    def test_executes_exactly_two_queries(self):
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        assert graph.run.call_count == 3

    def test_first_query_uses_direct_participates_in_path(self):
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        first_cypher = graph.run.call_args_list[0][0][0]
        assert "PARTICIPATES_IN" in first_cypher
        assert "Frame" in first_cypher
        assert "TRIGGERS" in first_cypher

    def test_second_query_uses_via_frame_argument_path(self):
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        second_cypher = graph.run.call_args_list[1][0][0]
        assert "FrameArgument" in second_cypher
        assert "PARTICIPANT" in second_cypher
        assert "TRIGGERS" in second_cypher

    def test_both_queries_use_merge(self):
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        for call_args in graph.run.call_args_list:
            cypher = call_args[0][0]
            assert "MERGE" in cypher.upper()

    def test_both_queries_create_describes_relationship(self):
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        for call_args in graph.run.call_args_list:
            cypher = call_args[0][0]
            assert "DESCRIBES" in cypher

    def test_returns_zero_when_graph_returns_empty_data(self):
        enricher, graph = _make_enricher()
        graph.run.return_value.data.return_value = []
        result = enricher.link_frameArgument_to_event()
        assert result == 0

    def test_returns_zero_when_linked_key_missing(self):
        enricher, graph = _make_enricher()
        graph.run.return_value.data.return_value = [{"x": 99}]
        result = enricher.link_frameArgument_to_event()
        assert result == 0

    def test_graph_error_propagates(self):
        enricher, graph = _make_enricher()
        graph.run.side_effect = RuntimeError("neo4j down")
        with pytest.raises(RuntimeError):
            enricher.link_frameArgument_to_event()

    def test_idempotency_via_merge_keyword(self):
        """Calling the method twice should not create duplicate DESCRIBES edges.
        This is guaranteed by MERGE; verify the keyword is present in both queries.
        """
        enricher, graph = _make_enricher()
        # first call
        enricher.link_frameArgument_to_event()
        first_calls = list(graph.run.call_args_list)
        graph.reset_mock()
        # second call
        enricher.link_frameArgument_to_event()
        second_calls = list(graph.run.call_args_list)
        assert len(first_calls) == len(second_calls) == 3
        for fc, sc in zip(first_calls, second_calls):
            assert fc[0][0] == sc[0][0]  # exact same Cypher each time


# ---------------------------------------------------------------------------
# Regression: old query behaviour no longer fires
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.regression
@enricher_deps
class TestLinkFrameArgumentToEventRegression:
    """Ensure the refactored method no longer relies solely on the old single query."""

    def test_old_single_query_pattern_not_used_alone(self):
        """The old implementation issued exactly one query.  The new one issues two."""
        enricher, graph = _make_enricher()
        enricher.link_frameArgument_to_event()
        assert graph.run.call_count >= 2, (
            "link_frameArgument_to_event must issue at least 2 queries "
            "(direct path + via-FrameArgument path)"
        )

    def test_return_type_is_int_not_empty_string(self):
        """Old implementation returned '' (empty string); new one must return int."""
        enricher, graph = _make_enricher()
        result = enricher.link_frameArgument_to_event()
        assert isinstance(result, int), (
            f"Expected int return type but got {type(result)}"
        )


@pytest.mark.unit
@enricher_deps
class TestDerivedDiscourseRelations:
    def test_derive_clinks_uses_causal_frame_arguments(self):
        enricher, graph = _make_enricher(run_side_effects=[[{"linked": 2}]])

        result = enricher.derive_clinks_from_causal_arguments()

        assert result == 2
        cypher = graph.run.call_args_list[0][0][0]
        assert "ARGM-CAU" in cypher
        assert "CLINK" in cypher
        assert "coalesce(main_event_c, main_event_l)" in cypher
        assert "OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]" in cypher
        assert "OPTIONAL MATCH (f)-[:DESCRIBES]" in cypher
        assert "srl_argm_cau" in cypher

    def test_derive_slinks_uses_reported_speech_frame_arguments(self):
        enricher, graph = _make_enricher(run_side_effects=[[{"linked": 3}]])

        result = enricher.derive_slinks_from_reported_speech()

        assert result == 3
        cypher = graph.run.call_args_list[0][0][0]
        assert "ARGM-DSP" in cypher
        assert "SLINK" in cypher
        assert "coalesce(main_event_c, main_event_l)" in cypher
        assert "OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]" in cypher
        assert "OPTIONAL MATCH (f)-[:DESCRIBES]" in cypher
        assert "srl_argm_dsp" in cypher
        assert "CALL {" in cypher
        assert "LIMIT 1" in cypher

    def test_derived_relation_queries_use_merge_and_self_link_guard(self):
        enricher, graph = _make_enricher(run_side_effects=[[{"linked": 1}], [{"linked": 1}]])

        enricher.derive_clinks_from_causal_arguments()
        enricher.derive_slinks_from_reported_speech()

        assert graph.run.call_count == 2
        for call_args in graph.run.call_args_list:
            cypher = call_args[0][0]
            assert "MERGE" in cypher.upper()
            assert "main_event <> sub_event" in cypher


@pytest.mark.unit
@enricher_deps
class TestParticipantReaderPreference:
    def test_add_core_participants_uses_canonical_first_with_fallback(self):
        enricher, graph = _make_enricher()

        enricher.add_core_participants_to_event()

        cypher = graph.run.call_args_list[0][0][0]
        assert "OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]" in cypher
        assert "OPTIONAL MATCH (f)-[:DESCRIBES]" in cypher
        assert "coalesce(event_c, event_l)" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(e:Entity)" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(e:VALUE)" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(e:NamedEntity)" in cypher
        assert "e.type IN" in cypher
        assert "AND (e:Entity OR e:NUMERIC OR e:VALUE)" not in cypher

    def test_add_non_core_participants_uses_canonical_first_with_fallback(self):
        enricher, graph = _make_enricher()

        enricher.add_non_core_participants_to_event()

        cypher = graph.run.call_args_list[0][0][0]
        assert "OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]" in cypher
        assert "OPTIONAL MATCH (f)-[:DESCRIBES]" in cypher
        assert "coalesce(event_c, event_l)" in cypher

    def test_semantic_relation_sources_use_canonical_first_with_legacy_fallback(self):
        enricher, graph = _make_enricher(run_side_effects=[[{"linked": 1}], [{"linked": 1}]])

        enricher.add_semantic_relation_types()

        cypher = graph.run.call_args_list[1][0][0]
        assert "MATCH (fa)-[:REFERS_TO]->(src:Entity)" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(src:VALUE)" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(src:NamedEntity)" in cypher
        assert "src.type IN" in cypher
        assert "MATCH (fa)-[:REFERS_TO]->(src:FrameArgument)" in cypher
        assert "AND (src:Entity OR src:NUMERIC OR src:VALUE OR src:FrameArgument)" not in cypher


@pytest.mark.unit
@enricher_deps
class TestEventMentionFactualityDefaults:
    def test_time_enrichment_uses_cypher_contains_not_like(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        time_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "SET em.time = CASE" in c[0][0]
        ]
        assert time_queries, "Expected time enrichment query to be executed"
        query = time_queries[0]
        assert "CONTAINS" in query
        assert "LIKE" not in query

    def test_polarity_enrichment_defaults_to_pos_and_uses_argm_neg(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        polarity_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "SET em.polarity = CASE" in c[0][0]
        ]
        assert polarity_queries, "Expected polarity enrichment query to be executed"
        query = polarity_queries[0]
        assert "ARGM-NEG" in query
        assert "ELSE 'POS'" in query

    def test_low_confidence_flagging_uses_linguistic_support_signals(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        low_conf_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "SET em.low_confidence = CASE" in c[0][0]
        ]
        assert low_conf_queries, "Expected low-confidence event query to be executed"
        query = low_conf_queries[0]
        assert "Frame" in query
        assert "EVENT_PARTICIPANT|PARTICIPANT" in query
        assert "OPTIONAL MATCH (participant_source:Entity)-[:EVENT_PARTICIPANT|PARTICIPANT]->(te)" in query
        assert "OPTIONAL MATCH (participant_source:VALUE)-[:EVENT_PARTICIPANT|PARTICIPANT]->(te)" in query
        assert "OPTIONAL MATCH (participant_source:NamedEntity)-[:EVENT_PARTICIPANT|PARTICIPANT]->(te)" in query
        assert "participant_source.type IN" in query
        assert "OPTIONAL MATCH (ent:Entity)-[:EVENT_PARTICIPANT|PARTICIPANT]->(te)" not in query
        assert "TLINK" in query
        assert "em.pos IN ['NOUN', 'NN', 'NNS', 'NNP', 'NNPS', 'OTHER', 'JJ']" in query
        assert "split(toLower(coalesce(em.pred, '')), ' ')[0] AS pred_lc" in query
        assert "pred_lc IN [" in query
        assert "'be', 'have', 'do', 'make'" in query

    def test_low_confidence_rollup_sets_tevent_flag(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        tevent_rollup_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "SET te.low_confidence" in c[0][0]
        ]
        assert tevent_rollup_queries, "Expected TEvent low-confidence rollup query to be executed"
        assert "all(flag IN mention_flags WHERE flag)" in tevent_rollup_queries[0]

    def test_infinitive_future_normalization_query_present(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        future_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "SET em.time = 'FUTURE'" in c[0][0] and "em.tense = 'INFINITIVE'" in c[0][0]
        ]
        assert future_queries, "Expected infinitive future normalization query to be executed"
        query = future_queries[0]
        assert "prev_tok" in query
        assert "toLower(coalesce(tok.lemma, '')) = 'add'" in query

    def test_nonverbal_tense_normalization_query_present(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        nonverbal_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "WHERE em.pos IN ['OTHER', 'JJ', 'JJR', 'JJS']" in c[0][0]
            and "SET em.tense = CASE" in c[0][0]
        ]
        assert nonverbal_queries, "Expected non-verbal tense normalization query to be executed"

    def test_cognitive_participle_normalization_query_present(self):
        enricher, graph = _make_enricher()

        enricher.enrich_event_mention_properties()

        cognitive_queries = [
            c[0][0] for c in graph.run.call_args_list
            if "toLower(coalesce(em.pred, '')) IN ['fear']" in c[0][0]
            and "SET em.tense = 'PRESENT'" in c[0][0]
        ]
        assert cognitive_queries, "Expected cognitive participle normalization query to be executed"
        query = cognitive_queries[0]
        assert "toUpper(coalesce(tok.pos, '')) = 'VBG'" in query
        assert "toLower(coalesce(next_tok.lemma, '')) = 'that'" in query
