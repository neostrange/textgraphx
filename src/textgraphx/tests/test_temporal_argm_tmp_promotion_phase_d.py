"""Phase-D tests for ARGM-TMP → TimexMention candidate promotion (D1).

``TemporalPhase.promote_argm_tmp_to_timex_candidates`` converts ARGM-TMP
FrameArgument spans not already covered by HeidelTime into SRLTimexCandidate
nodes so downstream TLINK rules can anchor events to those temporal expressions.

These tests verify:
1. The method exists on TemporalPhase and runs against the graph.
2. The Cypher only targets ARGM-TMP args from non-provisional frames.
3. HeidelTime-covered spans are excluded (no overlap guard).
4. The wrapper wires the call in the correct position (after
   materialize_timexes_fallback, before materialize_glinks).
5. Wrapper errors from the method are non-fatal (AttributeError guard).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

TEMPORAL_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "temporal.py"
)
WRAPPER_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "runtime" / "phase_wrappers.py"
)


@pytest.fixture(scope="module")
def temporal_source() -> str:
    return TEMPORAL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wrapper_source() -> str:
    return WRAPPER_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found in source"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


# ---------------------------------------------------------------------------
# Source-level contract assertions on TemporalPhase
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestArgmTmpPromotionMethodContract:
    """Verify the Cypher contract inside promote_argm_tmp_to_timex_candidates."""

    @pytest.fixture(scope="class")
    def method_src(self, temporal_source):
        return _extract_method(temporal_source, "promote_argm_tmp_to_timex_candidates")

    def test_method_exists(self, temporal_source):
        assert "def promote_argm_tmp_to_timex_candidates(" in temporal_source

    def test_targets_argm_tmp_only(self, method_src):
        """Must only process ARGM-TMP FrameArguments."""
        assert "ARGM-TMP" in method_src

    def test_skips_provisional_frames(self, method_src):
        """Non-provisional guard must be present."""
        assert "provisional" in method_src

    def test_excludes_heideltime_covered_spans(self, method_src):
        """Must not create candidates that overlap existing TimexMention nodes."""
        # The exclusion is expressed as NOT EXISTS or similar anti-join pattern
        assert "NOT" in method_src and ("TimexMention" in method_src or "TIMEX" in method_src)

    def test_creates_srl_timex_candidate_label(self, method_src):
        """Produced nodes must carry the SRLTimexCandidate label."""
        assert "SRLTimexCandidate" in method_src

    def test_creates_canonical_timex_and_refers_to_bridge(self, method_src):
        """SRL candidates must participate in the TimexMention -> TIMEX split."""
        assert "MERGE (t:TIMEX" in method_src
        assert "MERGE (tm)-[:REFERS_TO]->(t)" in method_src

    def test_uses_merge_for_idempotency(self, method_src):
        assert "MERGE" in method_src

    def test_source_property_set_to_srl_argm_tmp(self, method_src):
        """Provenance must trace back to SRL."""
        assert "srl_argm_tmp" in method_src

    def test_confidence_is_advisory(self, method_src):
        """Advisory-tier confidence must be set (< 0.90)."""
        import re
        confs = re.findall(r"confidence\s*=\s*([\d.]+)", method_src)
        assert confs, "No confidence value found in method"
        assert all(float(c) < 0.90 for c in confs), (
            f"Confidence too high for advisory-tier candidates: {confs}"
        )

    def test_scoped_by_doc_id(self, method_src):
        """Must accept and use doc_id for document-scoped processing."""
        assert "doc_id" in method_src


# ---------------------------------------------------------------------------
# Mock-execution: method calls graph.run
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_promote_argm_tmp_calls_graph_run():
    """promote_argm_tmp_to_timex_candidates must call self.graph.run at least once."""
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    temporal = TemporalPhase.__new__(TemporalPhase)
    temporal.graph = MagicMock()
    temporal.graph.run.return_value.data.return_value = []

    temporal.promote_argm_tmp_to_timex_candidates("42")

    assert temporal.graph.run.called


@pytest.mark.unit
def test_promote_argm_tmp_candidate_query_contains_argm_tmp():
    """The executed Cypher must reference ARGM-TMP."""
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    temporal = TemporalPhase.__new__(TemporalPhase)
    temporal.graph = MagicMock()
    temporal.graph.run.return_value.data.return_value = []

    temporal.promote_argm_tmp_to_timex_candidates("99")

    call_args = temporal.graph.run.call_args_list
    combined_query = " ".join(str(c[0][0]) for c in call_args if c[0])
    assert "ARGM-TMP" in combined_query, (
        "Executed Cypher should filter on ARGM-TMP FrameArgument type"
    )


@pytest.mark.unit
def test_promote_argm_tmp_returns_int_count():
    """Method must return an integer count of created candidates."""
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    temporal = TemporalPhase.__new__(TemporalPhase)
    temporal.graph = MagicMock()
    temporal.graph.run.return_value.data.return_value = [{"created": 3}]

    result = temporal.promote_argm_tmp_to_timex_candidates("1")

    assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Wrapper wiring assertions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestArgmTmpWiringInWrapper:
    """Verify the wrapper calls promote_argm_tmp_to_timex_candidates."""

    def test_wrapper_calls_promote_argm_tmp(self, wrapper_source):
        """Wrapper source must reference promote_argm_tmp_to_timex_candidates."""
        assert "promote_argm_tmp_to_timex_candidates" in wrapper_source

    def test_promotion_after_timexes_fallback(self, wrapper_source):
        """Promotion must be called after materialize_timexes_fallback (HeidelTime first)."""
        idx_fallback = wrapper_source.find("materialize_timexes_fallback")
        idx_promote = wrapper_source.find("promote_argm_tmp_to_timex_candidates")
        assert idx_fallback != -1, "materialize_timexes_fallback not found in wrapper"
        assert idx_promote != -1, "promote_argm_tmp_to_timex_candidates not found in wrapper"
        assert idx_promote > idx_fallback, (
            "promote_argm_tmp_to_timex_candidates must come AFTER materialize_timexes_fallback"
        )

    def test_promotion_before_materialize_glinks(self, wrapper_source):
        """Promotion must happen before materialize_glinks."""
        idx_promote = wrapper_source.find("promote_argm_tmp_to_timex_candidates")
        idx_glinks = wrapper_source.find("materialize_glinks")
        assert idx_glinks != -1, "materialize_glinks not found in wrapper"
        assert idx_promote < idx_glinks, (
            "promote_argm_tmp_to_timex_candidates must come BEFORE materialize_glinks"
        )

    def test_wrapper_guards_attribute_error(self, wrapper_source):
        """Wrapper must guard against AttributeError for backward compatibility."""
        # The guard is in a try/except AttributeError block around the call
        promote_idx = wrapper_source.find("promote_argm_tmp_to_timex_candidates")
        surrounding = wrapper_source[max(0, promote_idx - 400): promote_idx + 400]
        assert "AttributeError" in surrounding, (
            "Wrapper should guard promote_argm_tmp_to_timex_candidates call "
            "with try/except AttributeError for backward compatibility"
        )

    def test_progress_counter_accounts_for_new_step(self, wrapper_source):
        """ProgressLogger total ops should be 6 per document (was 5 before D1)."""
        import re
        # Find the ProgressLogger instantiation in TemporalPhaseWrapper
        match = re.search(
            r"ProgressLogger\(self\.logger,\s*len\(document_ids\)\s*\*\s*(\d+)",
            wrapper_source,
        )
        assert match, "ProgressLogger instantiation not found in wrapper"
        ops_per_doc = int(match.group(1))
        assert ops_per_doc == 6, (
            f"Expected 6 ops/doc after adding ARGM-TMP step, got {ops_per_doc}"
        )
