"""Phase-D tests for TLINK cases 8, 9, and 10 — NOMBANK nominal event endpoints (D3).

Static source-inspection + lightweight mock tests.  No live Neo4j or spaCy required.

Case 8: NOMBANK-sourced TEvent anchored to Document Creation Time (mirrors case6
        but lifts the ``pos NOT IN ['NN','NNS','NNP']`` exclusion that case6 applies).
Case 9: NOMBANK-sourced TEvent linked to sentence-co-occurring TIMEX3 nodes
        (proximity-based; SRLTimexCandidate nodes excluded to avoid circularity).
Case 10: NOMBANK-sourced TEvent linked to SRLTimexCandidate mentions only when
     the candidate originates from the event's own ARGM-TMP frame argument.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

TR_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "tlinks_recognizer.py"
)
WRAPPER_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "runtime" / "phase_wrappers.py"
)


@pytest.fixture(scope="module")
def tr_source() -> str:
    return TR_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wrapper_source() -> str:
    return WRAPPER_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: build a TlinksRecognizer with a mocked graph
# ---------------------------------------------------------------------------


def _make_recognizer(return_value=None):
    from textgraphx.pipeline.phases.tlinks_recognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = return_value or [{"created": 0}]
    return obj


def _extract_method(source: str, method_name: str) -> str:
    import re
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


# ===========================================================================
# Case 8: NOMBANK event → DCT anchor
# ===========================================================================


@pytest.mark.unit
class TestCase8NombankDct:
    """Case 8 query contract and structural tests."""

    @pytest.fixture(scope="class")
    def method_src(self, tr_source):
        return _extract_method(tr_source, "create_tlinks_case8")

    def test_method_exists(self, tr_source):
        assert "def create_tlinks_case8(" in tr_source

    def test_targets_nombank_source_events(self, method_src):
        """Must only target TEvents with source='nombank_srl'."""
        assert "nombank_srl" in method_src

    def test_anchors_to_dct(self, method_src):
        """Must traverse to CREATED_ON DCT node."""
        assert "CREATED_ON" in method_src

    def test_dct_label_check(self, method_src):
        """Must check that DCT is TIMEX or Timex3."""
        assert "TIMEX" in method_src or "Timex3" in method_src

    def test_default_reltype_is_included(self, method_src):
        """Default IS_INCLUDED is correct for nominal events without tense."""
        assert "IS_INCLUDED" in method_src

    def test_rule_id_present(self, method_src):
        """rule_id must be set on the TLINK for auditability."""
        assert "case8_nombank_dct" in method_src

    def test_uses_merge_not_create(self, method_src):
        """Must use MERGE for idempotency.  ON CREATE SET (MERGE conditional) is allowed."""
        import re
        assert "MERGE" in method_src
        # Reject bare CREATE (...) node/relationship creation; allow ON CREATE SET
        assert not re.search(r"\bCREATE\s*\(", method_src), (
            "create_tlinks_case8 must not use bare CREATE node/rel syntax; use MERGE"
        )

    def test_confidence_lower_than_structural_cases(self, method_src):
        """Proximity-based cases should have lower confidence than structure-based."""
        # case8 confidence is 0.65, structural cases are ≥0.78
        assert "0.65" in method_src

    def test_returns_count(self):
        """Method must return data from the graph query."""
        recognizer = _make_recognizer([{"created": 3}])
        rows = recognizer.create_tlinks_case8()
        assert rows[0]["created"] == 3

    def test_rule_id_in_executed_query(self):
        """Executed Cypher must include the rule_id constant."""
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case8()
        query = recognizer.graph.run.call_args[0][0]
        assert "case8_nombank_dct" in query

    def test_nombank_srl_filter_in_executed_query(self):
        """Executed Cypher must filter on source='nombank_srl'."""
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case8()
        query = recognizer.graph.run.call_args[0][0]
        assert "nombank_srl" in query

    def test_case8_excludes_low_confidence_events(self, method_src):
        assert "coalesce(e.low_confidence, false) = false" in method_src

    def test_case8_requires_timeml_core_events(self, method_src):
        assert "coalesce(e.is_timeml_core, true) = true" in method_src

    def test_case6_exclusion_gap_addressed(self, tr_source):
        """case6 must NOT exclude NN-pos tokens; case8 fills that gap.

        This test documents the design intent: case6 is NOT fixed (it handles
        verbal events only by design); case8 adds coverage for nominal events.
        """
        case6_src = _extract_method(tr_source, "create_tlinks_case6")
        # case6 excludes NN pos — confirming the gap case8 was built to fill
        assert "NN" in case6_src, (
            "case6 should still exclude NN-pos tokens; if this changes, case8 may be redundant"
        )


# ===========================================================================
# Case 9: NOMBANK event → sentence-local TIMEX
# ===========================================================================


@pytest.mark.unit
class TestCase9NombankSentenceTimex:
    """Case 9 query contract and structural tests."""

    @pytest.fixture(scope="class")
    def method_src(self, tr_source):
        return _extract_method(tr_source, "create_tlinks_case9")

    def test_method_exists(self, tr_source):
        assert "def create_tlinks_case9(" in tr_source

    def test_targets_nombank_source_events(self, method_src):
        assert "nombank_srl" in method_src

    def test_matches_within_same_sentence(self, method_src):
        """Both TEvent and TIMEX tokens must share the same Sentence node."""
        assert "Sentence" in method_src

    def test_excludes_srl_timex_candidates(self, method_src):
        """Must not use SRL-derived TIMEX candidates to avoid circular evidence."""
        assert "SRLTimexCandidate" in method_src
        assert "NOT tm:SRLTimexCandidate" in method_src

    def test_optional_match_for_canonical_timex(self, method_src):
        """Should resolve TimexMention → REFERS_TO → TIMEX for canonical target."""
        assert "REFERS_TO" in method_src or "t_ref" in method_src

    def test_default_reltype_is_included(self, method_src):
        assert "IS_INCLUDED" in method_src

    def test_rule_id_present(self, method_src):
        assert "case9_nombank_sentence_timex" in method_src

    def test_uses_merge_not_create(self, method_src):
        import re
        assert "MERGE" in method_src
        # Reject bare CREATE (...) node/relationship creation; allow ON CREATE SET
        assert not re.search(r"\bCREATE\s*\(", method_src)

    def test_confidence_is_0_60(self, method_src):
        """Sentence-proximity confidence must be lower than argument-structure cases."""
        assert "0.60" in method_src

    def test_uses_sentence_token_distance_window(self, method_src):
        """Must require local token proximity to avoid loose same-sentence matches."""
        assert "abs(coalesce(tok_e.tok_index_doc, -1) - coalesce(tok_t.tok_index_doc, -1)) <= 8" in method_src

    def test_returns_count(self):
        recognizer = _make_recognizer([{"created": 5}])
        rows = recognizer.create_tlinks_case9()
        assert rows[0]["created"] == 5

    def test_rule_id_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case9()
        query = recognizer.graph.run.call_args[0][0]
        assert "case9_nombank_sentence_timex" in query

    def test_sentence_traversal_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case9()
        query = recognizer.graph.run.call_args[0][0]
        assert "Sentence" in query

    def test_distance_window_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case9()
        query = recognizer.graph.run.call_args[0][0]
        assert "<= 8" in query

    def test_srl_timex_exclusion_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case9()
        query = recognizer.graph.run.call_args[0][0]
        assert "SRLTimexCandidate" in query

    def test_case9_excludes_low_confidence_events(self, method_src):
        assert "coalesce(e.low_confidence, false) = false" in method_src

    def test_case9_requires_timeml_core_events(self, method_src):
        assert "coalesce(e.is_timeml_core, true) = true" in method_src


# ===========================================================================
# Case 10: NOMBANK event → SRLTimexCandidate via matching ARGM-TMP evidence
# ===========================================================================


@pytest.mark.unit
class TestCase10NombankSrlTimex:
    """Case 10 query contract and structural tests."""

    @pytest.fixture(scope="class")
    def method_src(self, tr_source):
        return _extract_method(tr_source, "create_tlinks_case10")

    def test_method_exists(self, tr_source):
        assert "def create_tlinks_case10(" in tr_source

    def test_targets_nombank_source_events(self, method_src):
        assert "nombank_srl" in method_src

    def test_targets_srl_timex_candidates(self, method_src):
        assert "SRLTimexCandidate" in method_src

    def test_requires_argm_tmp_frame_argument(self, method_src):
        assert "ARGM-TMP" in method_src

    def test_joins_on_source_fa_id(self, method_src):
        assert "tm.source_fa_id = fa.id" in method_src

    def test_resolves_candidate_to_canonical_timex(self, method_src):
        assert "OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)" in method_src
        assert "WHERE t IS NOT NULL" in method_src

    def test_excludes_provisional_frames(self, method_src):
        assert "coalesce(f.provisional, false) = false" in method_src

    def test_excludes_low_confidence_events(self, method_src):
        assert "coalesce(e.low_confidence, false) = false" in method_src

    def test_requires_timeml_core_events(self, method_src):
        assert "coalesce(e.is_timeml_core, true) = true" in method_src

    def test_default_reltype_is_included(self, method_src):
        assert "IS_INCLUDED" in method_src

    def test_rule_id_present(self, method_src):
        assert "case10_nombank_srl_timex" in method_src

    def test_confidence_is_0_58(self, method_src):
        assert "0.58" in method_src

    def test_uses_merge_not_create(self, method_src):
        import re
        assert "MERGE" in method_src
        assert not re.search(r"\bCREATE\s*\(", method_src)

    def test_returns_count(self):
        recognizer = _make_recognizer([{"created": 2}])
        rows = recognizer.create_tlinks_case10()
        assert rows[0]["created"] == 2

    def test_rule_id_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case10()
        query = recognizer.graph.run.call_args[0][0]
        assert "case10_nombank_srl_timex" in query

    def test_source_fa_join_in_executed_query(self):
        recognizer = _make_recognizer()
        recognizer.create_tlinks_case10()
        query = recognizer.graph.run.call_args[0][0]
        assert "tm.source_fa_id = fa.id" in query


# ===========================================================================
# Run sequence: both cases wired in __main__ and phase_wrappers
# ===========================================================================


@pytest.mark.unit
class TestCase8Case9Case10Wiring:
    """Verify case8/case9/case10 appear in the canonical run sequences."""

    def test_case8_wired_in_main(self, tr_source):
        main_block = tr_source[tr_source.rfind("if __name__"):]
        assert "create_tlinks_case8" in main_block, (
            "create_tlinks_case8 must be called in __main__ run sequence"
        )

    def test_case9_wired_in_main(self, tr_source):
        main_block = tr_source[tr_source.rfind("if __name__"):]
        assert "create_tlinks_case9" in main_block

    def test_case10_wired_in_main(self, tr_source):
        main_block = tr_source[tr_source.rfind("if __name__"):]
        assert "create_tlinks_case10" in main_block

    def test_case8_wired_in_phase_wrapper(self, wrapper_source):
        assert "create_tlinks_case8" in wrapper_source

    def test_case9_wired_in_phase_wrapper(self, wrapper_source):
        assert "create_tlinks_case9" in wrapper_source

    def test_case10_wired_in_phase_wrapper(self, wrapper_source):
        assert "create_tlinks_case10" in wrapper_source

    def test_case8_label_in_phase_wrapper(self, wrapper_source):
        assert "Case 8: NOMBANK Event" in wrapper_source

    def test_case10_label_in_phase_wrapper(self, wrapper_source):
        assert "Case 10: NOMBANK Event" in wrapper_source

    def test_case9_label_in_phase_wrapper(self, wrapper_source):
        assert "Case 9: NOMBANK Event" in wrapper_source

    def test_cases_after_case7_in_main(self, tr_source):
        """case8/case9 must appear after case7 in the run sequence."""
        main_block = tr_source[tr_source.rfind("if __name__"):]
        pos7 = main_block.find("create_tlinks_case7")
        pos8 = main_block.find("create_tlinks_case8")
        pos9 = main_block.find("create_tlinks_case9")
        assert pos7 < pos8 < pos9, (
            "TLINK cases must run in order: case7 → case8 → case9"
        )

    def test_phase_metadata_includes_case8_case9(self, tr_source):
        """PhaseRun marker metadata must list case8 and case9."""
        assert "case8" in tr_source
        assert "case9" in tr_source

    def test_case6_uses_explicit_tense_gate(self, tr_source):
        """case6 should only anchor morphologically tensed events to DCT."""
        case6_src = _extract_method(tr_source, "create_tlinks_case6")
        assert "coalesce(e.tense, '') IN ['PAST', 'PRESENT', 'FUTURE']" in case6_src

    def test_case6_excludes_low_confidence_or_noncore_events(self, tr_source):
        """case6 should avoid anchoring low-confidence or non-TimeML-core events."""
        case6_src = _extract_method(tr_source, "create_tlinks_case6")
        assert "coalesce(e.low_confidence, false) = false" in case6_src
        assert "coalesce(e.is_timeml_core, true) = true" in case6_src
