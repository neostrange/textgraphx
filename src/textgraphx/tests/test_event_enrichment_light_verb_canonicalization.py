"""Tests for Step 6: light-verb canonicalization in merge_aligns_with_event_clusters.

Verifies that the light-verb inversion pass (Pass 0) correctly:
- Redirects EventMention REFERS_TO from verbal TEvent to nominal TEvent
- Transfers tense/aspect from verbal to nominal
- Marks the verbal TEvent as merged with merged_by='light_verb_canonicalization'
- Runs before the general ALIGNS_WITH merge pass (Pass 1+)
- Uses is_light_verb_host=true as the trigger signal
- Applies provisional guards on both frames

No live Neo4j required: source-inspection only.
"""
from pathlib import Path

import pytest

EEP_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"
)


@pytest.fixture(scope="module")
def eep_source() -> str:
    return EEP_PATH.read_text(encoding="utf-8")


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
# Light-verb pass existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_light_verb_pass_present(method_src):
    """merge_aligns_with_event_clusters must contain a light-verb-specific pass."""
    assert "is_light_verb_host" in method_src


@pytest.mark.unit
def test_light_verb_canonicalization_label(method_src):
    """merged_by must be set to 'light_verb_canonicalization'."""
    assert "light_verb_canonicalization" in method_src


# ---------------------------------------------------------------------------
# Ordering: Pass 0 before Pass 1
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lv_pass_runs_before_sense_conflict_pass(method_src):
    """Light-verb pass (Pass 0) must appear before the general sense-conflict pass (Pass 1)."""
    # Skip the docstring by searching from the first 'logger.debug(' call
    code_start = method_src.find("logger.debug(")
    assert code_start != -1, "Could not locate start of method code"
    code_section = method_src[code_start:]
    pos_lv = code_section.find("is_light_verb_host")
    pos_p1 = code_section.find("sense_conflict_query")
    assert pos_lv != -1 and pos_p1 != -1, \
        f"Markers not found: is_light_verb_host={pos_lv}, sense_conflict_query={pos_p1}"
    assert pos_lv < pos_p1, \
        "Light-verb pass must precede sense-conflict pass in method body"


# ---------------------------------------------------------------------------
# Light-verb redirect pass guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLightVerbRedirectGuards:
    def test_provisional_guard_on_verbal_frame(self, method_src):
        """Verbal frame must be non-provisional."""
        assert "provisional" in method_src

    def test_provisional_guard_on_nominal_frame(self, method_src):
        """Nominal frame must be non-provisional."""
        # Both are guarded in the same WHERE clause
        assert "provisional" in method_src and "f_nominal" in method_src

    def test_element_id_inequality_guard(self, method_src):
        """Must guard that the two TEvent nodes are distinct (elementId)."""
        assert "elementId(e_verbal) <> elementId(e_nominal)" in method_src or \
               "elementId(e_verbal) <>" in method_src

    def test_verbal_event_not_already_merged(self, method_src):
        """Must skip verbal TEvents already marked as merged."""
        assert "e_verbal" in method_src and "merged" in method_src

    def test_follows_aligns_with_edge(self, method_src):
        """Must traverse the ALIGNS_WITH edge to reach the nominal frame."""
        assert "ALIGNS_WITH" in method_src and "f_nominal" in method_src


# ---------------------------------------------------------------------------
# Tense/aspect transfer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tense_transferred_to_nominal_event(method_src):
    """Tense must be transferred from verbal to nominal TEvent using coalesce."""
    assert "e_nominal.tense" in method_src and "e_verbal.tense" in method_src


@pytest.mark.unit
def test_aspect_transferred_to_nominal_event(method_src):
    """Aspect must be transferred from verbal to nominal TEvent using coalesce."""
    assert "e_nominal.aspect" in method_src and "e_verbal.aspect" in method_src


@pytest.mark.unit
def test_tense_transfer_uses_coalesce(method_src):
    """Tense transfer must use coalesce to avoid overwriting existing values."""
    assert "coalesce(e_nominal.tense" in method_src


# ---------------------------------------------------------------------------
# EventMention redirect
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lv_refers_to_redirect_written(method_src):
    """A new REFERS_TO edge with source='light_verb_canonicalization' must be MERGE'd."""
    assert "light_verb_canonicalization" in method_src


@pytest.mark.unit
def test_lv_redirect_uses_merge(method_src):
    """REFERS_TO redirect must use MERGE for idempotency."""
    # The light-verb section runs from 'lv_redirect_query' to 'lv_mark_query'
    lv_start = method_src.find("lv_redirect_query")
    lv_end = method_src.find("lv_mark_query")
    assert lv_start != -1 and lv_end != -1
    lv_section = method_src[lv_start:lv_end]
    assert "MERGE (em)" in lv_section or "MERGE (em)-" in lv_section


@pytest.mark.unit
def test_lv_redirect_stores_merged_from(method_src):
    """The new REFERS_TO edge must record merged_from for provenance."""
    assert "merged_from" in method_src


@pytest.mark.unit
def test_lv_redirect_confidence_high(method_src):
    """Light-verb redirect confidence should be ≥ 0.80."""
    # 0.85 is the spec value
    assert "0.85" in method_src


# ---------------------------------------------------------------------------
# Mark-merged pass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lv_mark_merged_true(method_src):
    """Verbal TEvent must be marked merged=true."""
    # The mark pass runs from 'lv_mark_query' to 'sense_conflict_query'
    lv_start = method_src.find("lv_mark_query")
    lv_end = method_src.find("sense_conflict_query")
    assert lv_start != -1 and lv_end != -1
    lv_section = method_src[lv_start:lv_end]
    assert "e_verbal.merged" in lv_section or "merged      = true" in lv_section


@pytest.mark.unit
def test_lv_merged_into_set(method_src):
    """merged_into must reference the canonical nominal TEvent id."""
    assert "merged_into" in method_src and "e_nominal.id" in method_src


# ---------------------------------------------------------------------------
# Non-fatal exception handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lv_pass_has_exception_guard(method_src):
    """Light-verb passes must be wrapped in try/except to remain non-fatal."""
    assert "logger.exception" in method_src
