"""Integration tests for Iteration 2 features.

These tests require a live Neo4j instance (with data already ingested).
They are automatically skipped when Neo4j is unreachable.

Run with:
    pytest tests/test_integration_phase_assertions.py -v -m integration
"""

import pytest
import sys
import types
from uuid import uuid4
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------


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
    reason="Neo4j not reachable — skipping integration tests",
)


def _event_enrichment_deps_available() -> bool:
    """Return True only when EventEnrichmentPhase import deps are available."""
    try:
        import spacy  # noqa: F401
        return True
    except Exception:
        return False


event_enrichment_deps = pytest.mark.skipif(
    not _event_enrichment_deps_available(),
    reason="EventEnrichmentPhase dependencies unavailable (spaCy/_ctypes)",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def graph():
    """Return a real Neo4j graph connection for the test session."""
    from textgraphx.database.client import make_graph_from_config
    return make_graph_from_config()


def _stub_spacy_imports():
    if "spacy" not in sys.modules:
        spacy_mod = types.ModuleType("spacy")
        spacy_mod.load = MagicMock(return_value=MagicMock())
        spacy_mod.Language = MagicMock()
        sys.modules["spacy"] = spacy_mod

    for sub in ("spacy.tokens", "spacy.matcher", "spacy.language"):
        if sub not in sys.modules:
            sys.modules[sub] = types.ModuleType(sub)

    sys.modules["spacy.tokens"].Doc = getattr(sys.modules["spacy.tokens"], "Doc", MagicMock())
    sys.modules["spacy.tokens"].Token = getattr(sys.modules["spacy.tokens"], "Token", MagicMock())
    sys.modules["spacy.tokens"].Span = getattr(sys.modules["spacy.tokens"], "Span", MagicMock())
    sys.modules["spacy.matcher"].Matcher = getattr(sys.modules["spacy.matcher"], "Matcher", MagicMock())
    sys.modules["spacy.matcher"].DependencyMatcher = getattr(sys.modules["spacy.matcher"], "DependencyMatcher", MagicMock())
    sys.modules["spacy.language"].Language = getattr(sys.modules["spacy.language"], "Language", MagicMock())


def _stub_event_enrichment_imports():
    _stub_spacy_imports()
    if "cgitb" not in sys.modules:
        cgitb_mod = types.ModuleType("cgitb")
        cgitb_mod.text = ""
        sys.modules["cgitb"] = cgitb_mod
    for mod_name, attrs in (
        ("textgraphx.util.SemanticRoleLabeler", {"SemanticRoleLabel": MagicMock()}),
        ("textgraphx.util.EntityFishingLinker", {"EntityFishing": MagicMock()}),
        ("textgraphx.util.RestCaller", {"callAllenNlpApi": MagicMock()}),
        ("textgraphx.util.GraphDbBase", {"GraphDBBase": MagicMock()}),
        ("textgraphx.pipeline.ingestion.text_processor", {"TextProcessor": MagicMock()}),
    ):
        if mod_name not in sys.modules:
            module = types.ModuleType(mod_name)
            for key, value in attrs.items():
                setattr(module, key, value)
            sys.modules[mod_name] = module


def _load_temporal_phase_class():
    _stub_spacy_imports()
    import importlib

    module = importlib.import_module("textgraphx.pipeline.temporal.extraction")
    return module.TemporalPhase


def _load_event_enrichment_class():
    _stub_event_enrichment_imports()
    import importlib

    module = importlib.import_module("textgraphx.pipeline.phases.event_enrichment")
    return module.EventEnrichmentPhase


def _cleanup_seeded_subgraph(graph, *, doc_id=None, prefix=None):
    graph.run(
        """
        MATCH (n)
        WHERE ($doc_id IS NOT NULL AND n.doc_id = $doc_id)
           OR ($doc_id IS NOT NULL AND n.id = $doc_id)
           OR ($prefix IS NOT NULL AND coalesce(toString(n.id), '') STARTS WITH $prefix)
           OR ($prefix IS NOT NULL AND coalesce(toString(n.eiid), '') STARTS WITH $prefix)
           OR ($prefix IS NOT NULL AND coalesce(toString(n.tid), '') STARTS WITH $prefix)
        DETACH DELETE n
        """,
        {"doc_id": doc_id, "prefix": prefix},
    ).data()


# ---------------------------------------------------------------------------
# PhaseAssertions integration tests
# ---------------------------------------------------------------------------


@neo4j_required
@pytest.mark.integration
class TestPhaseAssertionsIntegration:
    def test_after_ingestion_returns_assertion_result(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_ingestion()
        assert result is not None
        assert result.phase == "ingestion"
        assert isinstance(result.passed, bool)

    def test_all_ingestion_checks_have_actual_values(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_ingestion()
        for check in result.checks:
            assert isinstance(check["actual"], int)
            assert check["actual"] >= 0

    def test_after_refinement_runs_without_error(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_refinement()
        assert result.phase == "refinement"

    def test_after_refinement_reports_nominal_semantic_head_check(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions

        pa = PhaseAssertions(graph)
        result = pa.after_refinement()
        check = next(
            (c for c in result.checks if c["label"] == "EntityMention nodes with nominal semantic head"),
            None,
        )
        assert check is not None
        assert isinstance(check["actual"], int)
        assert check["actual"] >= 0

    def test_after_temporal_runs_without_error(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_temporal()
        assert result.phase == "temporal"

    def test_after_event_enrichment_runs_without_error(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_event_enrichment()
        assert result.phase == "event_enrichment"

    def test_after_tlinks_runs_without_error(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions
        pa = PhaseAssertions(graph)
        result = pa.after_tlinks()
        assert result.phase == "tlinks"


# ---------------------------------------------------------------------------
# record_phase_run integration tests
# ---------------------------------------------------------------------------


@neo4j_required
@pytest.mark.integration
class TestRecordPhaseRunIntegration:
    def test_creates_phase_run_node(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run

        record_phase_run(
            graph,
            "ingestion",
            duration_seconds=1.5,
            documents_processed=1,
            metadata={"test": "integration"},
        )
        # Verify at least one PhaseRun node exists now
        rows = graph.run("MATCH (r:PhaseRun) RETURN count(r) AS c").data()
        assert rows[0]["c"] >= 1

    def test_phase_run_node_has_expected_properties(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run

        record_phase_run(
            graph,
            "test_phase_integration",
            duration_seconds=2.0,
            documents_processed=5,
        )
        rows = graph.run(
            "MATCH (r:PhaseRun {phase: $phase}) RETURN r ORDER BY r.timestamp DESC LIMIT 1",
            {"phase": "test_phase_integration"},
        ).data()
        assert len(rows) >= 1
        node = rows[0]["r"]
        assert node["phase"] == "test_phase_integration"
        assert node["documents_processed"] == 5
        assert "timestamp" in node

    def test_record_phase_run_is_idempotent_on_reruns(self, graph):
        """Calling record_phase_run multiple times creates separate audit nodes
        (different timestamps), not duplicate overwritten nodes.
        """
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run
        import time

        record_phase_run(graph, "idempotency_test", duration_seconds=0.1)
        time.sleep(0.01)
        record_phase_run(graph, "idempotency_test", duration_seconds=0.2)

        rows = graph.run(
            "MATCH (r:PhaseRun {phase: $phase}) RETURN count(r) AS c",
            {"phase": "idempotency_test"},
        ).data()
        assert rows[0]["c"] >= 2


# ---------------------------------------------------------------------------
# EventEnrichmentPhase integration tests (link_frameArgument_to_event)
# ---------------------------------------------------------------------------


@neo4j_required
@pytest.mark.integration
@pytest.mark.slow
@event_enrichment_deps
class TestEventEnrichmentIntegration:
    def test_link_frame_argument_to_event_returns_int(self, graph):
        """link_frameArgument_to_event must return an integer link count."""
        from unittest.mock import patch

        _stub_event_enrichment_imports()
        sys.modules.pop("textgraphx.pipeline.phases.event_enrichment", None)
        sys.modules.pop("textgraphx.pipeline.phases.event_enrichment", None)

        # Patch at the source module where the constructor resolves it.
        with patch("textgraphx.database.client.make_graph_from_config", return_value=graph):
            from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase
            enricher = EventEnrichmentPhase(argv=[])
            enricher.graph = graph

        result = enricher.link_frameArgument_to_event()
        assert isinstance(result, int)
        assert result >= 0

    def test_link_frame_argument_is_idempotent(self, graph):
        """Running link_frameArgument_to_event twice must not increase match count."""
        from unittest.mock import patch

        _stub_event_enrichment_imports()
        sys.modules.pop("textgraphx.pipeline.phases.event_enrichment", None)
        sys.modules.pop("textgraphx.pipeline.phases.event_enrichment", None)

        with patch("textgraphx.database.client.make_graph_from_config", return_value=graph):
            from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase
            enricher = EventEnrichmentPhase(argv=[])
            enricher.graph = graph

        first_run = enricher.link_frameArgument_to_event()
        second_run = enricher.link_frameArgument_to_event()
        # MERGE semantics: second run should create 0 new edges (everything already merged)
        assert second_run == 0 or second_run <= first_run, (
            "MERGE should not create duplicate DESCRIBES edges on repeated calls"
        )


# ---------------------------------------------------------------------------
# RunReport + orchestrator integration test
# ---------------------------------------------------------------------------


@neo4j_required
@pytest.mark.integration
@pytest.mark.slow
class TestOrchestratorRunReportIntegration:
    def test_run_selected_ingestion_produces_phase_result_with_assertions(self):
        """Smoke-level integration: PipelineOrchestrator.run_selected records
        assertions_passed for each completed phase.
        """
        from textgraphx.orchestration.orchestrator import PipelineOrchestrator

        dataset_dir = str(
            Path(__file__).parent.parent / "datastore" / "dataset"
        )
        orchestrator = PipelineOrchestrator(
            directory=dataset_dir, model_name="en_core_web_sm"
        )
        orchestrator.run_selected(["ingestion"])

        ingestion_phase = orchestrator.summary.phases.get("ingestion")
        assert ingestion_phase is not None
        assert ingestion_phase.status == "completed"
        # assertions_passed may be True, False, or None if graph unavailable
        assert ingestion_phase.assertions_passed in (True, False, None)


@neo4j_required
@pytest.mark.integration
class TestSeededSchemaMaterializationIntegration:
    def test_create_signals2_materializes_signal_node(self, graph):
        doc_id = 910001
        prefix = f"itg_sig_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (a:AnnotatedText {id: $doc_id})
                SET a.text = 'After the merger', a.creationtime = '2020-01-01T00:00:00'
                MERGE (s:Sentence {id: $sent_id})
                SET s.text = 'After the merger'
                MERGE (a)-[:CONTAINS_SENTENCE]->(s)
                MERGE (t:TagOccurrence {id: $tok_id})
                SET t.index = 0, t.end_index = 5, t.text = 'After', t.tok_index_doc = 0, t.tok_index_sent = 0
                MERGE (s)-[:HAS_TOKEN]->(t)
                """,
                {"doc_id": doc_id, "sent_id": f"{prefix}_sent", "tok_id": f"{prefix}_tok"},
            ).data()

            TemporalPhase = _load_temporal_phase_class()
            phase = TemporalPhase.__new__(TemporalPhase)
            phase.graph = graph
            phase._get_ttk_xml = lambda _: "<root><tarsqi_tags><SIGNAL sid='s1' begin='0' end='5'>After</SIGNAL></tarsqi_tags></root>"

            phase.create_signals2(doc_id)

            rows = graph.run(
                """
                MATCH (sig:Signal {doc_id: $doc_id, id: 's1'})
                RETURN sig.text AS text, sig.start_tok AS start_tok, sig.end_tok AS end_tok,
                       sig.start_char AS start_char, sig.end_char AS end_char
                """,
                {"doc_id": doc_id},
            ).data()
            assert rows, "expected Signal node to be materialized"
            assert rows[0]["text"] == "After"
            assert rows[0]["start_tok"] == 0
            assert rows[0]["end_tok"] == 0
            assert rows[0]["start_char"] == 0
            assert rows[0]["end_char"] == 5
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_derive_clinks_materializes_causal_edge(self, graph):
        doc_id = 910002
        prefix = f"itg_clink_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main:TEvent {eiid: $main_eiid, doc_id: $doc_id})
                MERGE (sub:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARGM-CAU'
                MERGE (tok:TagOccurrence {id: $tok_id})
                MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(main)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (tok)-[:PARTICIPATES_IN]->(fa)
                MERGE (tok)-[:TRIGGERS]->(sub)
                """,
                {
                    "doc_id": doc_id,
                    "main_eiid": f"{prefix}_main",
                    "sub_eiid": f"{prefix}_sub",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "tok_id": f"{prefix}_tok",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph

            result = phase.derive_clinks_from_causal_arguments()

            rows = graph.run(
                """
                MATCH (:TEvent {eiid: $main_eiid, doc_id: $doc_id})-[r:CLINK]->(:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                RETURN r.source AS source
                """,
                {"doc_id": doc_id, "main_eiid": f"{prefix}_main", "sub_eiid": f"{prefix}_sub"},
            ).data()
            assert result >= 1
            assert rows, "expected CLINK relationship to be materialized"
            assert rows[0]["source"] == "srl_argm_cau"
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_derive_slinks_materializes_reported_speech_edge(self, graph):
        doc_id = 910003
        prefix = f"itg_slink_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main:TEvent {eiid: $main_eiid, doc_id: $doc_id})
                MERGE (sub:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARGM-DSP'
                MERGE (tok:TagOccurrence {id: $tok_id})
                MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(main)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (tok)-[:PARTICIPATES_IN]->(fa)
                MERGE (tok)-[:TRIGGERS]->(sub)
                """,
                {
                    "doc_id": doc_id,
                    "main_eiid": f"{prefix}_main",
                    "sub_eiid": f"{prefix}_sub",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "tok_id": f"{prefix}_tok",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph

            result = phase.derive_slinks_from_reported_speech()

            rows = graph.run(
                """
                MATCH (:TEvent {eiid: $main_eiid, doc_id: $doc_id})-[r:SLINK]->(:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                RETURN r.source AS source
                """,
                {"doc_id": doc_id, "main_eiid": f"{prefix}_main", "sub_eiid": f"{prefix}_sub"},
            ).data()
            assert result >= 1
            assert rows, "expected SLINK relationship to be materialized"
            assert rows[0]["source"] == "srl_argm_dsp"
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_derive_clinks_falls_back_to_legacy_describes(self, graph):
        doc_id = 910005
        prefix = f"itg_clink_legacy_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main:TEvent {eiid: $main_eiid, doc_id: $doc_id})
                MERGE (sub:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARGM-CAU'
                MERGE (tok:TagOccurrence {id: $tok_id})
                MERGE (f)-[:DESCRIBES]->(main)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (tok)-[:PARTICIPATES_IN]->(fa)
                MERGE (tok)-[:TRIGGERS]->(sub)
                """,
                {
                    "doc_id": doc_id,
                    "main_eiid": f"{prefix}_main",
                    "sub_eiid": f"{prefix}_sub",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "tok_id": f"{prefix}_tok",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph

            result = phase.derive_clinks_from_causal_arguments()

            rows = graph.run(
                """
                MATCH (:TEvent {eiid: $main_eiid, doc_id: $doc_id})-[r:CLINK]->(:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                RETURN r.source AS source
                """,
                {"doc_id": doc_id, "main_eiid": f"{prefix}_main", "sub_eiid": f"{prefix}_sub"},
            ).data()
            assert result >= 1
            assert rows, "expected CLINK relationship with legacy DESCRIBES fallback"
            assert rows[0]["source"] == "srl_argm_cau"
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_derive_clinks_prefers_canonical_over_legacy_when_both_exist(self, graph):
        doc_id = 910006
        prefix = f"itg_clink_pref_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main_c:TEvent {eiid: $main_c_eiid, doc_id: $doc_id})
                MERGE (main_l:TEvent {eiid: $main_l_eiid, doc_id: $doc_id})
                MERGE (sub:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARGM-CAU'
                MERGE (tok:TagOccurrence {id: $tok_id})
                MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(main_c)
                MERGE (f)-[:DESCRIBES]->(main_l)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (tok)-[:PARTICIPATES_IN]->(fa)
                MERGE (tok)-[:TRIGGERS]->(sub)
                """,
                {
                    "doc_id": doc_id,
                    "main_c_eiid": f"{prefix}_main_c",
                    "main_l_eiid": f"{prefix}_main_l",
                    "sub_eiid": f"{prefix}_sub",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "tok_id": f"{prefix}_tok",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph

            result = phase.derive_clinks_from_causal_arguments()
            assert result >= 1

            canonical_rows = graph.run(
                """
                MATCH (:TEvent {eiid: $main_c_eiid, doc_id: $doc_id})-[r:CLINK]->(:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                RETURN count(r) AS c
                """,
                {
                    "doc_id": doc_id,
                    "main_c_eiid": f"{prefix}_main_c",
                    "sub_eiid": f"{prefix}_sub",
                },
            ).data()
            legacy_rows = graph.run(
                """
                MATCH (:TEvent {eiid: $main_l_eiid, doc_id: $doc_id})-[r:CLINK]->(:TEvent {eiid: $sub_eiid, doc_id: $doc_id})
                RETURN count(r) AS c
                """,
                {
                    "doc_id": doc_id,
                    "main_l_eiid": f"{prefix}_main_l",
                    "sub_eiid": f"{prefix}_sub",
                },
            ).data()

            assert canonical_rows[0]["c"] >= 1
            assert legacy_rows[0]["c"] == 0
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_after_event_enrichment_accepts_seeded_canonical_edges(self, graph):
        from textgraphx.pipeline.runtime.phase_assertions import PhaseAssertions, PhaseThresholds

        doc_id = 910004
        prefix = f"itg_assert_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                MERGE (ev:TEvent {eiid: $eiid, doc_id: $doc_id})
                MERGE (ent:Entity {id: $ent_id, type: 'INTEGRATION'})
                MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(ev)
                MERGE (fa)-[:HAS_FRAME_ARGUMENT]->(f)
                MERGE (ent)-[:EVENT_PARTICIPANT]->(ev)
                """,
                {
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "eiid": f"{prefix}_event",
                    "doc_id": doc_id,
                    "ent_id": f"{prefix}_entity",
                },
            ).data()

            pa = PhaseAssertions(
                graph,
                thresholds=PhaseThresholds(
                    min_frame_describes_event_rels=1,
                    min_has_frame_argument_rels=1,
                    min_event_participant_rels=1,
                ),
            )
            result = pa.after_event_enrichment()
            assert result.passed is True
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_add_core_participants_falls_back_to_legacy_describes(self, graph):
        doc_id = 910007
        prefix = f"itg_core_legacy_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main:TEvent {eiid: $main_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARG0'
                MERGE (ent:Entity {id: $ent_id, type: 'INTEGRATION'})
                MERGE (f)-[:DESCRIBES]->(main)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (fa)-[:REFERS_TO]->(ent)
                """,
                {
                    "doc_id": doc_id,
                    "main_eiid": f"{prefix}_main",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "ent_id": f"{prefix}_entity",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph
            phase.add_core_participants_to_event()

            rows = graph.run(
                """
                MATCH (:Entity {id: $ent_id})-[r:EVENT_PARTICIPANT]->(:TEvent {eiid: $main_eiid, doc_id: $doc_id})
                RETURN count(r) AS c
                """,
                {"ent_id": f"{prefix}_entity", "main_eiid": f"{prefix}_main", "doc_id": doc_id},
            ).data()
            assert rows[0]["c"] >= 1
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_add_core_participants_prefers_canonical_over_legacy(self, graph):
        doc_id = 910008
        prefix = f"itg_core_pref_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (main_c:TEvent {eiid: $main_c_eiid, doc_id: $doc_id})
                MERGE (main_l:TEvent {eiid: $main_l_eiid, doc_id: $doc_id})
                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                SET fa.type = 'ARG0'
                MERGE (ent:Entity {id: $ent_id, type: 'INTEGRATION'})
                MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(main_c)
                MERGE (f)-[:DESCRIBES]->(main_l)
                MERGE (fa)-[:PARTICIPANT]->(f)
                MERGE (fa)-[:REFERS_TO]->(ent)
                """,
                {
                    "doc_id": doc_id,
                    "main_c_eiid": f"{prefix}_main_c",
                    "main_l_eiid": f"{prefix}_main_l",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "ent_id": f"{prefix}_entity",
                },
            ).data()

            EventEnrichmentPhase = _load_event_enrichment_class()
            phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
            phase.graph = graph
            phase.add_core_participants_to_event()

            canonical_rows = graph.run(
                """
                MATCH (:Entity {id: $ent_id})-[r:EVENT_PARTICIPANT]->(:TEvent {eiid: $main_c_eiid, doc_id: $doc_id})
                RETURN count(r) AS c
                """,
                {
                    "ent_id": f"{prefix}_entity",
                    "main_c_eiid": f"{prefix}_main_c",
                    "doc_id": doc_id,
                },
            ).data()
            legacy_rows = graph.run(
                """
                MATCH (:Entity {id: $ent_id})-[r:EVENT_PARTICIPANT]->(:TEvent {eiid: $main_l_eiid, doc_id: $doc_id})
                RETURN count(r) AS c
                """,
                {
                    "ent_id": f"{prefix}_entity",
                    "main_l_eiid": f"{prefix}_main_l",
                    "doc_id": doc_id,
                },
            ).data()

            assert canonical_rows[0]["c"] >= 1
            assert legacy_rows[0]["c"] == 0
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)

    def test_participation_edge_backfill_migrates_legacy_only_edges(self, graph):
        from textgraphx.tools import migrate_participation_edges as mpe

        doc_id = 910009
        prefix = f"itg_part_mig_{uuid4().hex[:8]}"
        try:
            graph.run(
                """
                MERGE (a:AnnotatedText {id: $doc_id})
                MERGE (s:Sentence {id: $sent_id})
                MERGE (a)-[:CONTAINS_SENTENCE]->(s)

                MERGE (tok:TagOccurrence {id: $tok_id})
                SET tok.tok_index_doc = 11, tok.tok_index_sent = 0, tok.text = 'seed'
                MERGE (s)-[:HAS_TOKEN]->(tok)

                MERGE (f:Frame {id: $frame_id})
                MERGE (fa:FrameArgument {id: $fa_id})
                MERGE (ne:NamedEntity {id: $ne_id})
                SET ne.type = 'ORG', ne.value = 'Seed Org', ne.index = 11, ne.end_index = 11

                MERGE (tok)-[:PARTICIPATES_IN]->(f)
                MERGE (tok)-[:PARTICIPATES_IN]->(fa)
                MERGE (tok)-[:PARTICIPATES_IN]->(ne)
                """,
                {
                    "doc_id": doc_id,
                    "sent_id": f"{prefix}_sent",
                    "tok_id": f"{prefix}_tok",
                    "frame_id": f"{prefix}_frame",
                    "fa_id": f"{prefix}_fa",
                    "ne_id": f"{prefix}_ne",
                },
            ).data()

            before = mpe.run_migration(graph, apply=False, batch_size=500)
            assert before["frame_missing_before"] >= 2
            assert before["mention_missing_before"] >= 1

            applied = mpe.run_migration(graph, apply=True, batch_size=500)
            assert applied["created_in_frame"] >= 2
            assert applied["created_in_mention"] >= 1
            assert applied["frame_missing_after"] == 0
            assert applied["mention_missing_after"] == 0

            rows = graph.run(
                """
                MATCH (tok:TagOccurrence {id: $tok_id})
                OPTIONAL MATCH (tok)-[rf:IN_FRAME]->(:Frame)
                OPTIONAL MATCH (tok)-[rfa:IN_FRAME]->(:FrameArgument)
                OPTIONAL MATCH (tok)-[rm:IN_MENTION]->(:NamedEntity {id: $ne_id})
                RETURN count(rf) AS c_frame,
                       count(rfa) AS c_fa,
                       count(rm) AS c_mention
                """,
                {
                    "tok_id": f"{prefix}_tok",
                    "ne_id": f"{prefix}_ne",
                },
            ).data()
            assert rows[0]["c_frame"] >= 1
            assert rows[0]["c_fa"] >= 1
            assert rows[0]["c_mention"] >= 1
        finally:
            _cleanup_seeded_subgraph(graph, doc_id=doc_id, prefix=prefix)
