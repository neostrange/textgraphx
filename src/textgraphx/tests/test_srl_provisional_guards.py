"""Source-inspection tests for provisional-frame safety guards (Audit Step 2, D1, D2).

These tests are static — they parse production source files and validate that:
- ``link_frameArgument_to_event`` in event_enrichment.py rejects provisional frames
  via ``coalesce(f.provisional, false) = false`` in both query paths.
- The TEvent fallback query in temporal.py excludes NOMBANK frames
  via ``f.framework IS NULL OR f.framework = 'PROPBANK'`` and ``coalesce(f.provisional, false) = false``.
- ``promote_argm_tmp_to_timex_candidates`` exists and is wired into the temporal run sequence.
- ``promote_nombank_frames_to_tevents`` exists in event_enrichment.py and is wired.

No Neo4j or spaCy instance is required.
"""

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Source fixtures
# ---------------------------------------------------------------------------

EEP_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"
)
TEMPORAL_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "temporal.py"
)


@pytest.fixture(scope="module")
def eep_source() -> str:
    return EEP_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def temporal_source() -> str:
    return TEMPORAL_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    """Return source text from ``def method_name(`` to the next top-level method."""
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found in source"
    next_def = re.search(r"\n    def ", source[start + len(method_name):])
    end = start + len(method_name) + next_def.start() if next_def else len(source)
    return source[start:end]


# ===========================================================================
# Step 2a: link_frameArgument_to_event provisional guards
# ===========================================================================


@pytest.mark.unit
class TestLinkFrameArgumentProvisionalGuard:
    """Validate that both Cypher paths guard on coalesce(f.provisional, false) = false."""

    @pytest.fixture(scope="class")
    def method_src(self, eep_source):
        return _extract_method(eep_source, "link_frameArgument_to_event")

    def test_provisional_guard_present(self, method_src):
        """The string 'coalesce(f.provisional, false) = false' must appear at least twice."""
        count = method_src.count("coalesce(f.provisional, false) = false")
        assert count >= 2, (
            f"Expected provisional guard in both query paths, found {count} occurrence(s). "
            "Both Path 1 (query_direct) and Path 2 (query_via_arg) must filter provisional frames."
        )

    def test_provisional_guard_path1_after_match(self, method_src):
        """Path 1: provisional guard must appear in query_direct string (near PARTICIPATES_IN)."""
        # Extract the query_direct string region
        qd_start = method_src.find("query_direct")
        qd_end = method_src.find("query_via_arg")
        assert qd_start != -1, "query_direct not found in method source"
        assert qd_end != -1, "query_via_arg not found in method source"
        path1_text = method_src[qd_start:qd_end]
        assert "coalesce(f.provisional, false) = false" in path1_text, (
            "Path 1 (query_direct) must include provisional guard"
        )

    def test_provisional_guard_path2_after_match(self, method_src):
        """Path 2: provisional guard must appear in query_via_arg string."""
        qva_start = method_src.find("query_via_arg")
        qvq_end = method_src.find("query_instantiates")
        assert qva_start != -1, "query_via_arg not found"
        path2_text = method_src[qva_start:qvq_end] if qvq_end != -1 else method_src[qva_start:]
        assert "coalesce(f.provisional, false) = false" in path2_text, (
            "Path 2 (query_via_arg) must include provisional guard"
        )

    def test_guard_uses_where_clause(self, method_src):
        """Guard must be a WHERE clause, not a property constraint in MATCH."""
        # Ensure the guard appears as a standalone WHERE condition
        assert re.search(r"WHERE\s+coalesce\(f\.provisional", method_src), (
            "provisional guard must use WHERE clause syntax"
        )


# ===========================================================================
# Step 2b: temporal.py TEvent fallback framework guard
# ===========================================================================


@pytest.mark.unit
class TestTemporalFallbackFrameworkGuard:
    """Validate temporal.py TEvent fallback excludes NOMBANK and provisional frames."""

    @pytest.fixture(scope="class")
    def method_src(self, temporal_source):
        return _extract_method(temporal_source, "materialize_tevents")

    def test_framework_guard_in_fallback_query(self, method_src):
        """Fallback query must exclude NOMBANK frames."""
        assert "f.framework IS NULL OR f.framework = 'PROPBANK'" in method_src or \
               "f.framework = 'PROPBANK'" in method_src, (
            "TEvent fallback query must filter out NOMBANK frames via framework guard"
        )

    def test_provisional_guard_in_fallback_query(self, method_src):
        """Fallback query must exclude provisional frames."""
        assert "coalesce(f.provisional, false) = false" in method_src, (
            "TEvent fallback query must filter out provisional frames"
        )


# ===========================================================================
# D1: promote_argm_tmp_to_timex_candidates
# ===========================================================================


@pytest.mark.unit
class TestPromoteArgmTmpToTimexCandidates:
    """Validate existence and structure of promote_argm_tmp_to_timex_candidates."""

    @pytest.fixture(scope="class")
    def method_src(self, temporal_source):
        return _extract_method(temporal_source, "promote_argm_tmp_to_timex_candidates")

    def test_method_exists(self, temporal_source):
        assert "def promote_argm_tmp_to_timex_candidates" in temporal_source

    def test_queries_argm_tmp_frame_arguments(self, method_src):
        """Must look for ARGM-TMP typed FrameArgument nodes."""
        assert "ARGM-TMP" in method_src

    def test_provisional_guard_on_frame(self, method_src):
        """Must exclude provisional frames when querying ARGM-TMP args."""
        assert "coalesce(f.provisional, false) = false" in method_src

    def test_creates_srl_timex_candidate_label(self, method_src):
        """Must create SRLTimexCandidate-labelled mention nodes."""
        assert "SRLTimexCandidate" in method_src

    def test_source_attribute_is_srl_argm_tmp(self, method_src):
        """TimexMention source must be 'srl_argm_tmp'."""
        assert "srl_argm_tmp" in method_src

    def test_confidence_is_0_65(self, method_src):
        """Confidence value must be 0.65 (advisory tier)."""
        assert "0.65" in method_src

    def test_needs_review_is_set(self, method_src):
        """needs_review flag must be set to mark advisory candidates."""
        assert "needs_review" in method_src

    def test_non_fatal_exception_handling(self, method_src):
        """Must not propagate exceptions — candidate query failure must be caught."""
        assert "except Exception" in method_src

    def test_wired_into_run_sequence(self, temporal_source):
        """Must be called in the __main__ temporal run sequence."""
        main_block = temporal_source[temporal_source.rfind("if __name__"):]
        assert "promote_argm_tmp_to_timex_candidates" in main_block, (
            "promote_argm_tmp_to_timex_candidates must be called in __main__ run sequence"
        )


# ===========================================================================
# D2: promote_nombank_frames_to_tevents
# ===========================================================================


@pytest.mark.unit
class TestPromoteNombankFramesToTevents:
    """Validate existence and structure of promote_nombank_frames_to_tevents."""

    @pytest.fixture(scope="class")
    def method_src(self, eep_source):
        return _extract_method(eep_source, "promote_nombank_frames_to_tevents")

    def test_method_exists(self, eep_source):
        assert "def promote_nombank_frames_to_tevents" in eep_source

    def test_targets_nombank_framework(self, method_src):
        """Must only match NOMBANK-framework frames."""
        assert "NOMBANK" in method_src

    def test_provisional_guard_on_frame(self, method_src):
        """Must exclude provisional NOMBANK frames."""
        assert "coalesce(f.provisional, false) = false" in method_src

    def test_skips_already_linked_frames(self, method_src):
        """Must skip frames that already have DESCRIBES/FRAME_DESCRIBES_EVENT to TEvent."""
        assert "NOT exists((f)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(:TEvent))" in method_src

    def test_requires_core_argument_support(self, method_src):
        """Must require ARG0/ARG1 evidence before promoting a nominal frame."""
        assert "fa_core:FrameArgument" in method_src
        assert "IN ['ARG0', 'ARG1', 'A0', 'A1']" in method_src

    def test_uses_is_eventive_filter(self, method_src):
        """Must call the eventive-nominal filter to avoid promoting non-events."""
        assert "_is_eventive" in method_src

    def test_creates_tevent_with_nombank_source(self, method_src):
        """Created TEvent must carry source='nombank_srl'."""
        assert "nombank_srl" in method_src

    def test_marks_promoted_event_as_timeml_core(self, method_src):
        """Promoted nominal events should be marked as TimeML-core by default."""
        assert "event.is_timeml_core = true" in method_src

    def test_clears_low_confidence_for_promoted_events(self, method_src):
        """Promotion path should initialize low_confidence=false."""
        assert "event.low_confidence = false" in method_src

    def test_creates_tevent_class_occurrence(self, method_src):
        """Created TEvent must have class='OCCURRENCE'."""
        assert "OCCURRENCE" in method_src

    def test_creates_tevent_pos_nn(self, method_src):
        """Created TEvent must carry pos='NN' to distinguish from verbal predicates."""
        assert "pos" in method_src and "'NN'" in method_src

    def test_deterministic_event_id(self, method_src):
        """Event ID must be deterministically derived (md5/hash, not random)."""
        assert "md5" in method_src or "hashlib" in method_src

    def test_merges_describes_edge(self, method_src):
        """Must MERGE DESCRIBES edge between NOMBANK frame and new TEvent."""
        assert "MERGE (f)-[:DESCRIBES]->(event)" in method_src

    def test_non_fatal_exception_handling(self, method_src):
        """Must not propagate exceptions."""
        assert "except Exception" in method_src

    def test_wired_into_event_enrichment_run_sequence(self, eep_source):
        """Must be called in the __main__ event_enrichment run sequence."""
        main_block = eep_source[eep_source.rfind("if __name__"):]
        assert "promote_nombank_frames_to_tevents" in main_block, (
            "promote_nombank_frames_to_tevents must be called in __main__ run sequence"
        )
