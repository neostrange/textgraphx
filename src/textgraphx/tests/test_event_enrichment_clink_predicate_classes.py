"""Tests for EventEnrichmentPhase.derive_clinks_from_predicate_classes (Phase E3).

Source-inspection tests covering:
- Module-level causal predicate constant structure
- Cypher query: PropBank-only, non-provisional, non-merged guards
- clink_type CASE assignment for CAUSE / ENABLE / PREVENT
- Confidence calibration per class
- Wiring in __main__ and phase_wrappers.py

No live Neo4j or spaCy required.
"""

from pathlib import Path
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
    return _extract_method(eep_source, "derive_clinks_from_predicate_classes")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPredicateConstants:
    def test_cause_lemmas_defined(self, eep_source):
        assert "_CLINK_CAUSE_LEMMAS" in eep_source

    def test_enable_lemmas_defined(self, eep_source):
        assert "_CLINK_ENABLE_LEMMAS" in eep_source

    def test_prevent_lemmas_defined(self, eep_source):
        assert "_CLINK_PREVENT_LEMMAS" in eep_source

    def test_all_lemmas_union_defined(self, eep_source):
        assert "_CLINK_ALL_LEMMAS" in eep_source

    def test_key_cause_predicates_present(self, eep_source):
        for lemma in ("cause", "lead", "trigger", "force", "produce"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in CAUSE inventory"

    def test_key_enable_predicates_present(self, eep_source):
        for lemma in ("allow", "enable", "permit", "help"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in ENABLE inventory"

    def test_key_prevent_predicates_present(self, eep_source):
        for lemma in ("prevent", "stop", "block", "ban"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in PREVENT inventory"


# ---------------------------------------------------------------------------
# Method existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def derive_clinks_from_predicate_classes(" in eep_source


# ---------------------------------------------------------------------------
# Cypher guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryGuards:
    def test_only_propbank_frames_queried(self, method_src):
        """Must restrict to PROPBANK frames (not NOMBANK or untagged)."""
        assert "framework: 'PROPBANK'" in method_src or 'framework: "PROPBANK"' in method_src

    def test_provisional_guard(self, method_src):
        """Must exclude provisional frames."""
        assert "provisional" in method_src

    def test_main_event_merged_guard(self, method_src):
        """Main event must not be merged."""
        assert "main_event" in method_src
        assert "merged" in method_src

    def test_sub_event_merged_guard(self, method_src):
        """Subordinate/caused event must not be merged."""
        assert "sub" in method_src and "merged" in method_src

    def test_same_doc_guard(self, method_src):
        """Both events must share doc_id to prevent cross-document CLINKs."""
        assert "doc_id" in method_src

    def test_arg1_arg2_path_used(self, method_src):
        """Must follow ARG1/ARG2 to reach the complement event."""
        assert "ARG1" in method_src and "ARG2" in method_src

    def test_uses_clink_all_lemmas_parameter(self, method_src):
        """Must parameterize the full causal lemma list (not hardcode)."""
        assert "$clink_all_lemmas" in method_src

    def test_uses_merge_for_idempotency(self, method_src):
        """Must MERGE the CLINK edge to remain idempotent."""
        assert "MERGE (main_event)-[cl:CLINK]->(sub)" in method_src or \
               "MERGE (main_event)-[cl:CLINK]" in method_src

    def test_lemma_normalisation_strips_sense_number(self, method_src):
        """Predicate lemma must be extracted from sense string (e.g. 'cause.01' → 'cause')."""
        assert "split(" in method_src and "'.')[0]" in method_src


# ---------------------------------------------------------------------------
# clink_type CASE assignment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClinkTypeAssignment:
    def test_cause_branch_is_default(self, method_src):
        """CAUSE must appear as a branch (ideally the ELSE default)."""
        assert "'CAUSE'" in method_src or '"CAUSE"' in method_src

    def test_enable_branch_assigned(self, method_src):
        """ENABLE clink_type must be set for enablement lemmas."""
        assert "'ENABLE'" in method_src or '"ENABLE"' in method_src

    def test_prevent_branch_assigned(self, method_src):
        """PREVENT clink_type must be set for prevention lemmas."""
        assert "'PREVENT'" in method_src or '"PREVENT"' in method_src

    def test_clink_type_property_set(self, method_src):
        """The cl.clink_type property must be written on the edge."""
        assert "cl.clink_type" in method_src


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfidenceCalibration:
    def test_cause_confidence_value(self, method_src):
        """Direct causation predicates carry the highest confidence (0.63)."""
        assert "0.63" in method_src

    def test_enable_confidence_value(self, method_src):
        """Enablement predicates carry slightly lower confidence (0.58)."""
        assert "0.58" in method_src

    def test_prevent_confidence_value(self, method_src):
        """Prevention predicates (0.60)."""
        assert "0.60" in method_src

    def test_confidence_hint_property_set(self, method_src):
        assert "cl.confidence_hint" in method_src


# ---------------------------------------------------------------------------
# Rule provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProvenance:
    def test_rule_id_set(self, method_src):
        assert "derive_clinks_from_predicate_classes_v1" in method_src

    def test_source_kind_rule(self, method_src):
        assert "source_kind" in method_src and "rule" in method_src

    def test_source_srl_propbank_causal(self, method_src):
        assert "srl_propbank_class" in method_src

    def test_link_semantics_causal(self, method_src):
        assert "causal" in method_src


# ---------------------------------------------------------------------------
# Exception safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExceptionSafety:
    def test_has_try_except(self, method_src):
        """Query errors must be caught and logged (non-fatal)."""
        assert "except" in method_src

    def test_returns_zero_on_failure(self, method_src):
        """Must return 0 on exception path."""
        assert "return 0" in method_src


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(eep_source):
    """__main__ block must call derive_clinks_from_predicate_classes."""
    assert "tp.derive_clinks_from_predicate_classes()" in eep_source


@pytest.mark.unit
def test_wired_after_causal_arguments_in_main(eep_source):
    """derive_clinks_from_predicate_classes must be called after derive_clinks_from_causal_arguments."""
    pos_existing = eep_source.find("tp.derive_clinks_from_causal_arguments()")
    pos_new = eep_source.find("tp.derive_clinks_from_predicate_classes()")
    assert pos_existing != -1 and pos_new != -1
    assert pos_new > pos_existing, \
        "derive_clinks_from_predicate_classes must be called after derive_clinks_from_causal_arguments"


@pytest.mark.unit
def test_wired_in_phase_wrappers(wrapper_source):
    """phase_wrappers.py enrichment_steps must include the new CLINK pass."""
    assert "derive_clinks_from_predicate_classes" in wrapper_source


@pytest.mark.unit
def test_wrappers_stamps_new_rule_id(wrapper_source):
    """phase_wrappers must call stamp_inferred_relationships for the new rule_id."""
    assert "derive_clinks_from_predicate_classes_v1" in wrapper_source
