"""Tests for EventEnrichmentPhase.merge_aligns_with_event_clusters (Phase D Refinement).

Static source-inspection + lightweight mock tests covering:
- The 4-pass structure (sense-conflict marking, EventMention redirect, TLINK transfer, mark merged)
- Sense-contradiction guard using coalesce(aw.sense_conflict, false)
- Provisional frame exclusion
- Already-merged TEvent exclusion
- Suppressed TLINK exclusion
- Confidence scaling on transferred TLINKs (0.9 factor)
- Wiring in __main__ and phase_wrappers.py

No live Neo4j or spaCy required.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

EEP_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"
)
WRAPPER_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "runtime" / "phase_wrappers.py"
)


@pytest.fixture(scope="module")
def eep_source() -> str:
    return EEP_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wrapper_source() -> str:
    return WRAPPER_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"{method_name!r} not found"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


@pytest.fixture(scope="module")
def method_src(eep_source):
    return _extract_method(eep_source, "merge_aligns_with_event_clusters")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def merge_aligns_with_event_clusters(" in eep_source


# ---------------------------------------------------------------------------
# Pass 1: sense-conflict guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass1SenseConflict:
    def test_sense_conflict_flag_set(self, method_src):
        """Must write sense_conflict=true on the ALIGNS_WITH edge."""
        assert "sense_conflict" in method_src
        assert "true" in method_src.lower() or "= true" in method_src

    def test_sense_conflict_detects_differing_senses(self, method_src):
        """Must compare the two frame sense values and flag when they differ."""
        assert "s1 <> s2" in method_src or "sense_canonical" in method_src

    def test_sense_conflict_only_when_both_non_empty(self, method_src):
        """Guard must require both senses to be non-empty to avoid spurious conflicts."""
        assert "s1 <> ''" in method_src and "s2 <> ''" in method_src

    def test_sense_conflict_stores_values_on_edge(self, method_src):
        """Both sense values should be stored on the edge for auditability."""
        assert "sense_canonical" in method_src
        assert "sense_secondary" in method_src


# ---------------------------------------------------------------------------
# Pass 2: EventMention redirect
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass2EventMentionRedirect:
    def test_skips_sense_conflicted_pairs(self, method_src):
        """Must not redirect EventMentions for sense-conflicting frame pairs."""
        assert "coalesce(aw.sense_conflict, false) = false" in method_src

    def test_skips_provisional_frames(self, method_src):
        """Provisional frames must be excluded from the merge."""
        assert "coalesce(f_canonical.provisional, false) = false" in method_src
        assert "coalesce(f_secondary.provisional, false) = false" in method_src

    def test_skips_already_merged_tevents(self, method_src):
        """Secondary TEvents already merged in a prior pass must be skipped."""
        assert "coalesce(e_secondary.merged, false) = false" in method_src

    def test_redirects_refers_to_edges(self, method_src):
        """Must create new REFERS_TO edge from EventMention to canonical TEvent."""
        assert "REFERS_TO" in method_src
        assert "e_canonical" in method_src

    def test_redirect_uses_merge(self, method_src):
        """Redirect must use MERGE, not CREATE, for idempotency."""
        assert "MERGE (em)-" in method_src or "MERGE (em)" in method_src

    def test_redirect_source_attribute(self, method_src):
        """Redirected edge must carry provenance source='aligns_with_merge'."""
        assert "aligns_with_merge" in method_src

    def test_redirect_confidence(self, method_src):
        """Redirected REFERS_TO edge must carry a confidence value."""
        assert "0.80" in method_src


# ---------------------------------------------------------------------------
# Pass 3: TLINK transfer
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass3TlinkTransfer:
    """Verify that TLINK transfer (formerly Passes 3a/3b) is absent.

    TlinksRecognizer now guards merged events with coalesce(e.merged,false)=false,
    so TLINKs are never created for secondary events in the first place.  TLINK
    creation is exclusively owned by TlinksRecognizer (architectural contract).
    """

    def test_no_tlink_merge_in_event_enrichment(self, method_src):
        """TLINK creation must not appear in merge_aligns_with_event_clusters."""
        import re
        tlink_create = re.search(r"MERGE.*TLINK|CREATE.*TLINK", method_src, re.IGNORECASE)
        assert not tlink_create, (
            "merge_aligns_with_event_clusters must not create TLINKs; "
            "TLINK ownership belongs exclusively to TlinksRecognizer. "
            "Use coalesce(e.merged,false)=false guards in TlinksRecognizer instead."
        )

    def test_source_aligns_with_transfer_not_present(self, method_src):
        """'aligns_with_transfer' source label must not appear after TLINK removal."""
        assert "aligns_with_transfer" not in method_src


# ---------------------------------------------------------------------------
# Pass 4: mark secondary TEvents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass4MarkMerged:
    def test_sets_merged_true(self, method_src):
        """Secondary TEvent must be marked merged=true."""
        assert "merged      = true" in method_src or "merged = true" in method_src

    def test_sets_merged_into(self, method_src):
        """merged_into must store the canonical TEvent id for diagnostics."""
        assert "merged_into" in method_src

    def test_sets_merged_by(self, method_src):
        """merged_by must identify the method for provenance."""
        assert "merge_aligns_with_event_clusters" in method_src

    def test_only_acts_on_unmerged_tevents(self, method_src):
        """Must guard with coalesce(e_secondary.merged, false) = false."""
        assert "coalesce(e_secondary.merged, false) = false" in method_src


# ---------------------------------------------------------------------------
# Non-fatal exception handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_each_pass_wrapped_in_try_except(method_src):
    """All 3 passes must be independently wrapped; failure in one must not stop others."""
    count = method_src.count("except Exception")
    assert count >= 3, (
        f"Expected ≥3 independent except-Exception handlers (one per pass), found {count}"
    )


# ---------------------------------------------------------------------------
# Graph traversal: ALIGNS_WITH edge traversal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_traverses_aligns_with_edge(method_src):
    """Method must traverse the ALIGNS_WITH relationship created by Phase C."""
    assert "ALIGNS_WITH" in method_src


@pytest.mark.unit
def test_traverses_describes_frame_describes_event(method_src):
    """Must reach TEvents via DESCRIBES|FRAME_DESCRIBES_EVENT — the guarded paths."""
    assert "DESCRIBES|FRAME_DESCRIBES_EVENT" in method_src or (
        "DESCRIBES" in method_src and "FRAME_DESCRIBES_EVENT" in method_src
    )


# ---------------------------------------------------------------------------
# Mock execution: method callable + returns integer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_returns_merged_count():
    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

    obj = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    # 5 passes: lv_redirect (P0a), lv_mark (P0b), sense-conflict (P1), redirect (P2), mark (P4)
    mock_graph.run.return_value.data.side_effect = [
        [{"redirected": 0}],    # Pass 0a: light-verb EventMention redirect
        [{"marked": 0}],        # Pass 0b: light-verb mark-merged
        [{"conflicts": 0}],     # Pass 1: sense-conflict
        [{"redirected": 2}],    # Pass 2: ALIGNS_WITH redirect
        [{"marked": 3}],        # Pass 4: mark-merged
    ]
    obj.graph = mock_graph

    result = obj.merge_aligns_with_event_clusters()
    assert result == 3


@pytest.mark.unit
def test_method_tolerates_empty_results():
    """Must handle empty result sets from each pass without raising."""
    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

    obj = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = []
    obj.graph = mock_graph

    result = obj.merge_aligns_with_event_clusters()
    assert result == 0


@pytest.mark.unit
def test_method_tolerates_pass1_exception():
    """A failure in the sense-conflict pass must not prevent subsequent passes."""
    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

    obj = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    # LV passes succeed; sense-conflict (P1) raises; redirect and mark succeed
    mock_graph.run.return_value.data.side_effect = [
        [{"redirected": 0}],           # Pass 0a: lv redirect
        [{"marked": 0}],               # Pass 0b: lv mark
        RuntimeError("sense conflict DB error"),  # Pass 1: raises
        [{"redirected": 1}],           # Pass 2: redirect
        [{"marked": 1}],               # Pass 4: mark
    ]
    obj.graph = mock_graph

    # Must not raise; returns the marked count from pass 4
    result = obj.merge_aligns_with_event_clusters()
    assert result == 1


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_run_sequence(eep_source):
    main_block = eep_source[eep_source.rfind("if __name__"):]
    assert "merge_aligns_with_event_clusters" in main_block


@pytest.mark.unit
def test_wired_after_promote_nombank_in_main(eep_source):
    """merge must run after promote_nombank_frames_to_tevents in the run sequence."""
    main_block = eep_source[eep_source.rfind("if __name__"):]
    pos_nombank = main_block.find("promote_nombank_frames_to_tevents")
    pos_merge = main_block.find("merge_aligns_with_event_clusters")
    assert 0 < pos_nombank < pos_merge, (
        "merge_aligns_with_event_clusters must run after promote_nombank_frames_to_tevents"
    )


@pytest.mark.unit
def test_wired_in_phase_wrapper(wrapper_source):
    assert "merge_aligns_with_event_clusters" in wrapper_source


@pytest.mark.unit
def test_wrapper_label_descriptive(wrapper_source):
    assert "ALIGNS_WITH" in wrapper_source or "Merging" in wrapper_source


@pytest.mark.unit
def test_wrapper_order_after_promote_nombank(wrapper_source):
    """Wrapper must list merge after promote_nombank."""
    pos_nombank = wrapper_source.find("promote_nombank_frames_to_tevents")
    pos_merge = wrapper_source.find("merge_aligns_with_event_clusters")
    assert 0 < pos_nombank < pos_merge
