"""Regression tests for Iteration 2 pipeline phase behaviour.

These tests lock in the expected contracts of the new modules so that future
refactors don't inadvertently break them.  They use mocks, so no running
services are required.
"""

import json
from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.pipeline.runtime.phase_assertions import (
    PhaseAssertions,
    PhaseThresholds,
    AssertionResult,
    record_phase_run,
)
from textgraphx.evaluation.reports import RunReport, DocumentStatus


# ---------------------------------------------------------------------------
# Regression: PhaseAssertions API contract
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestPhaseAssertionsContract:
    """Verify the public API shape of PhaseAssertions doesn't change."""

    def test_all_phase_methods_exist(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]
        pa = PhaseAssertions(graph)
        for method in [
            "after_ingestion",
            "after_refinement",
            "after_temporal",
            "after_event_enrichment",
            "after_tlinks",
        ]:
            assert hasattr(pa, method), f"Missing method: {method}"
            assert callable(getattr(pa, method))

    def test_all_methods_return_assertion_result(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 0}]
        pa = PhaseAssertions(graph)
        for method_name in [
            "after_ingestion",
            "after_refinement",
            "after_temporal",
            "after_event_enrichment",
            "after_tlinks",
        ]:
            result = getattr(pa, method_name)()
            assert isinstance(result, AssertionResult), (
                f"{method_name} must return AssertionResult"
            )

    def test_assertion_result_has_required_fields(self):
        result = AssertionResult(phase="x", passed=True)
        assert hasattr(result, "phase")
        assert hasattr(result, "passed")
        assert hasattr(result, "checks")
        assert hasattr(result, "errors")

    def test_phase_thresholds_all_numeric(self):
        t = PhaseThresholds()
        for field_name, value in vars(t).items():
            assert isinstance(value, (int, float)), (
                f"PhaseThresholds.{field_name} must be numeric, got {type(value)}"
            )

    def test_after_ingestion_queries_three_node_types(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 0}]
        pa = PhaseAssertions(graph)
        pa.after_ingestion()
        assert graph.run.call_count == 3

    def test_check_dict_has_required_keys(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 5}]
        pa = PhaseAssertions(graph)
        result = pa.after_ingestion()
        for check in result.checks:
            assert "label" in check
            assert "actual" in check
            assert "minimum" in check
            assert "passed" in check


# ---------------------------------------------------------------------------
# Regression: RunReport API contract
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestRunReportContract:
    def test_mark_processed_fields_populated(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion", "refinement"])
        doc = report.documents[0]
        assert doc.status == "processed"
        assert doc.doc_id == "d1"
        assert "ingestion" in doc.phases_completed
        assert doc.failed_phase is None

    def test_mark_failed_fields_populated(self):
        report = RunReport()
        report.mark_failed("d2", "b.xml", "temporal", "timeout", ["ingestion"])
        doc = report.documents[0]
        assert doc.status == "failed"
        assert doc.failed_phase == "temporal"
        assert doc.reason == "timeout"
        assert "ingestion" in doc.phases_completed

    def test_mark_skipped_fields_populated(self):
        report = RunReport()
        report.mark_skipped("d3", "c.xml", "no text found")
        doc = report.documents[0]
        assert doc.status == "skipped"
        assert doc.reason == "no text found"

    def test_to_dict_stable_shape(self):
        report = RunReport(execution_id="stable-test")
        report.mark_processed("d1", "a.xml", ["ingestion"])
        d = report.to_dict()
        # Keys must be present in stable output
        required_keys = {"execution_id", "created_at", "summary", "documents", "phase_summary"}
        assert required_keys.issubset(d.keys())

    def test_summary_counts_never_negative(self):
        report = RunReport()
        assert report.processed_count >= 0
        assert report.skipped_count >= 0
        assert report.failed_count >= 0
        assert report.total_count >= 0

    def test_total_equals_sum_of_parts(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion"])
        report.mark_skipped("d2", "b.xml", "reason")
        report.mark_failed("d3", "c.xml", "ingestion", "err")
        assert report.total_count == (
            report.processed_count + report.skipped_count + report.failed_count
        )


# ---------------------------------------------------------------------------
# Regression: PhaseResult in orchestrator has assertions_passed
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestOrchestratorPhaseResult:
    def test_phase_result_has_assertions_passed_field(self):
        from textgraphx.orchestration.orchestrator import PhaseResult
        result = PhaseResult(name="ingestion", status="completed", duration=1.0)
        assert hasattr(result, "assertions_passed")
        assert result.assertions_passed is None  # default

    def test_phase_result_assertions_passed_can_be_set(self):
        from textgraphx.orchestration.orchestrator import PhaseResult
        result = PhaseResult(
            name="ingestion", status="completed", duration=1.0, assertions_passed=True
        )
        assert result.assertions_passed is True


# ---------------------------------------------------------------------------
# Regression: record_phase_run Cypher shape
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestRecordPhaseRunCypherShape:
    """Ensure record_phase_run always writes a PhaseRun node with correct props."""

    def test_cypher_merges_by_id(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(graph, "ingestion", duration_seconds=1.0)
        cypher = graph.run.call_args[0][0]
        assert "MERGE" in cypher
        assert "PhaseRun" in cypher
        assert "$id" in cypher

    def test_props_always_contains_phase_and_timestamp(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(graph, "refinement", duration_seconds=2.0)
        params = graph.run.call_args[0][1]
        assert "phase" in params["props"]
        assert "timestamp" in params["props"]

    def test_id_param_equals_timestamp(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(graph, "tlinks", duration_seconds=0.5)
        params = graph.run.call_args[0][1]
        assert params["id"] == params["props"]["timestamp"]

    def test_timestamp_is_timezone_aware_utc(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = []
        record_phase_run(graph, "ingestion", duration_seconds=1.0)
        params = graph.run.call_args[0][1]

        ts = datetime.fromisoformat(params["props"]["timestamp"])
        assert ts.tzinfo is not None
        assert ts.utcoffset() == timedelta(0)


@pytest.mark.regression
class TestRefinementRunMarkerContract:
    """Keep RefinementRun marker timestamp semantics stable."""

    def test_refinement_marker_uses_timezone_aware_utc_timestamp(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "MERGE (r:RefinementRun {id: $id})" in source
        assert "run_id = utc_iso_now()" in source
        assert '"id": run_id, "ts": run_id' in source

    def test_quantified_entity_rule_merges_entity_and_relationship_separately(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "merge (e:Entity {id: entity_id, type: 'NOMINAL'})" in source
        assert "merge (fa)-[:REFERS_TO]->(e)" in source

    def test_quantified_entity_rule_marks_partitive_metadata(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "THEN 'PARTITIVE'" in source
        assert "ELSE 'QUANTIFIED'" in source
        assert "e.nominalSubtype = nominal_subtype" in source
        assert "e.partitivePrep = 'of'" in source
        assert "e.partitiveObject = pobj.text" in source

    def test_quantified_entity_rule_only_deletes_numeric_namedentity_links(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "where ne.type in ['CARDINAL', 'QUANTITY', 'PERCENT', 'MONEY', 'ORDINAL']" in source

    def test_nominal_entity_id_generation_is_deterministic(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "'nominal_' + doc_part + '_' + toString(start_tok) + '_' + toString(end_tok) AS entity_id" in source
        assert "e.provenance_rule_id = 'refinement.link_frameArgument_to_new_entity'" in source

    def test_nominal_mentions_materialization_contains_required_metadata(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "def materialize_nominal_mentions_from_frame_arguments(self):" in source
        assert "def materialize_nominal_mentions_from_noun_chunks(self):" in source
        assert "em.syntactic_type = row.syntactic_type" in source
        assert "em.mention_source = 'frame_argument_nominal'" in source
        assert "em.mention_source = 'noun_chunk_nominal'" in source
        assert "MERGE (tok)-[:PARTICIPATES_IN]->(em)" in source
        assert "core_arg_hits > 0" in source
        assert "AND NOT chunk_text_lc =~ '.*[0-9].*'" in source
        assert "AND NOT chunk_text_lc IN ['yesterday', 'today', 'tomorrow']" in source

    def test_nominal_semantic_profile_annotation_is_additive(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "def resolve_nominal_semantic_heads(self):" in source
        assert '"resolve_nominal_semantic_heads",' in source
        assert "em.nominalSemanticHead = coalesce(semantic_head.lemma, semantic_head.text, em.head, em.value)" in source
        assert "em.nominalSemanticHeadSource = CASE" in source
        assert "def annotate_nominal_semantic_profiles(self):" in source
        assert "em.nominalEvalLayerSuggestion = eval_layer" in source
        assert "em.nominalEvalProfile = eval_profile" in source
        assert "em.nominalEvalCandidateGold = eval_candidate_gold" in source
        assert "em.nominalHeadWnLexname = head_wn_lexname" in source
        assert "em.nominalEventiveByWordNet = eventive_by_wordnet" in source
        assert "em.nominalEventiveByTrigger = event_trigger" in source
        assert "em.nominalEventiveByArgumentStructure = eventive_by_argument" in source
        assert "em.nominalEventiveByMorphology = eventive_by_morphology" in source
        assert "em.nominalEventiveConfidence = eventive_confidence" in source
        assert "em.nominalSemanticSignals = semantic_signals" in source
        assert "e.nominalEvalProfile = coalesce(e.nominalEvalProfile, eval_profile)" in source

    def test_named_entity_head_assignment_skips_prepopulated_heads(self):
        source = (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()

        assert "and f.headTokenIndex is null" in source
        assert "and c.headTokenIndex is null" in source


@pytest.mark.regression
def test_evaluator_wordnet_eventive_nominal_filter_present():
    source = (Path(__file__).parent.parent / "evaluation" / "meantime_evaluator.py").read_text()

    assert "def _is_wordnet_eventive_noun(features:" in source
    assert "head_nltk_synset" in source
    assert "head_hypernyms" in source
    assert "head_wn_lexname" in source
    assert "noun.event" in source


@pytest.mark.regression
def test_evaluator_nominal_profile_mode_projection_present():
    source = (Path(__file__).parent.parent / "evaluation" / "meantime_evaluator.py").read_text()

    assert "nominal_profile_mode: str = \"all\"" in source
    assert "allowed_profile_modes = {\"all\", \"eventive\", \"salient\", \"candidate-gold\", \"background\"}" in source
    assert "nominal_eval_profile" in source
    assert "nominal_eval_candidate_gold" in source


@pytest.mark.regression
def test_wordnet_token_enricher_persists_lexname_metadata():
    source = (Path(__file__).parent.parent / "text_processing_components" / "WordnetTokenEnricher.py").read_text()

    assert "wn_lexname = synset.lexname()" in source
    assert "t.wnLexname = $wnLexname" in source


@pytest.mark.regression
def test_refinement_wrapper_executes_nominal_mentions_family():
    source = (Path(__file__).parent.parent / "pipeline/runtime/phase_wrappers.py").read_text()

    assert 'refiner.run_rule_family("numeric_value")' in source
    assert 'refiner.run_rule_family("nominal_mentions")' in source
    assert 'refiner.run_rule_family("mention_cleanup")' in source

    assert source.index('refiner.run_rule_family("numeric_value")') < source.index(
        'refiner.run_rule_family("nominal_mentions")'
    )
    assert source.index('refiner.run_rule_family("nominal_mentions")') < source.index(
        'refiner.run_rule_family("mention_cleanup")'
    )
