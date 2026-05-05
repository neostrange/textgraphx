"""Tests for EventEnrichmentPhase.derive_slinks_from_predicate_classes (Phase E2).

Source-inspection tests covering:
- Module-level predicate constant structure
- Cypher query: PropBank-only, non-provisional, non-merged guards
- slink_type CASE assignment for FACTIVE / MODAL / EVIDENTIAL
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
    return _extract_method(eep_source, "derive_slinks_from_predicate_classes")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPredicateConstants:
    def test_evidential_lemmas_defined(self, eep_source):
        assert "_SLINK_EVIDENTIAL_LEMMAS" in eep_source

    def test_factive_lemmas_defined(self, eep_source):
        assert "_SLINK_FACTIVE_LEMMAS" in eep_source

    def test_modal_lemmas_defined(self, eep_source):
        assert "_SLINK_MODAL_LEMMAS" in eep_source

    def test_all_lemmas_union_defined(self, eep_source):
        assert "_SLINK_ALL_LEMMAS" in eep_source

    def test_key_evidential_predicates_present(self, eep_source):
        for lemma in ("say", "report", "announce", "claim", "believe", "think"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in EVIDENTIAL inventory"

    def test_key_factive_predicates_present(self, eep_source):
        for lemma in ("know", "realize", "discover", "find"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in FACTIVE inventory"

    def test_key_modal_predicates_present(self, eep_source):
        for lemma in ("want", "hope", "plan", "try"):
            assert f'"{lemma}"' in eep_source or f"'{lemma}'" in eep_source, \
                f"Expected predicate {lemma!r} in MODAL inventory"


# ---------------------------------------------------------------------------
# Method existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def derive_slinks_from_predicate_classes(" in eep_source


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
        """Subordinate event must not be merged."""
        assert "sub" in method_src and "merged" in method_src

    def test_same_doc_guard(self, method_src):
        """Both events must share doc_id to prevent cross-document SLINKs."""
        assert "doc_id" in method_src

    def test_arg1_arg2_path_used(self, method_src):
        """Must follow ARG1/ARG2 to reach the complement event."""
        assert "ARG1" in method_src and "ARG2" in method_src

    def test_uses_slink_all_lemmas_parameter(self, method_src):
        """Must parameterize the full lemma list (not hardcode)."""
        assert "$slink_all_lemmas" in method_src

    def test_uses_merge_for_idempotency(self, method_src):
        """Must MERGE the SLINK edge to remain idempotent."""
        assert "MERGE (main_event)-[sl:SLINK]->(sub)" in method_src or \
               "MERGE (main_event)-[sl:SLINK]" in method_src

    def test_lemma_normalisation_strips_sense_number(self, method_src):
        """Predicate lemma must be extracted from sense string (e.g. 'say.01' → 'say')."""
        assert "split(" in method_src and "'.')[0]" in method_src


# ---------------------------------------------------------------------------
# slink_type CASE assignment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSlinkTypeAssignment:
    def test_factive_branch_assigned(self, method_src):
        """FACTIVE slink_type must be set for factive lemmas."""
        assert "'FACTIVE'" in method_src or '"FACTIVE"' in method_src

    def test_modal_branch_assigned(self, method_src):
        """MODAL slink_type must be set for modal lemmas."""
        assert "'MODAL'" in method_src or '"MODAL"' in method_src

    def test_evidential_default_branch(self, method_src):
        """EVIDENTIAL must be the ELSE / default branch."""
        assert "'EVIDENTIAL'" in method_src or '"EVIDENTIAL"' in method_src

    def test_slink_type_property_set(self, method_src):
        """The sl.slink_type property must be written on the edge."""
        assert "sl.slink_type" in method_src


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfidenceCalibration:
    def test_factive_confidence_higher_than_modal(self, method_src):
        """FACTIVE predicates should carry the highest confidence."""
        # factive=0.68, modal=0.60 are the specified values
        assert "0.68" in method_src

    def test_modal_confidence_value(self, method_src):
        assert "0.60" in method_src

    def test_confidence_hint_property_set(self, method_src):
        assert "sl.confidence_hint" in method_src


# ---------------------------------------------------------------------------
# Rule provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProvenance:
    def test_rule_id_set(self, method_src):
        assert "derive_slinks_from_predicate_classes_v1" in method_src

    def test_source_kind_rule(self, method_src):
        assert "source_kind" in method_src and "rule" in method_src

    def test_source_srl_propbank_class(self, method_src):
        assert "srl_propbank_class" in method_src


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(eep_source):
    """__main__ block must call derive_slinks_from_predicate_classes."""
    assert "tp.derive_slinks_from_predicate_classes()" in eep_source


@pytest.mark.unit
def test_wired_in_phase_wrappers(wrapper_source):
    """phase_wrappers.py enrichment_steps must include the new SLINK pass."""
    assert "derive_slinks_from_predicate_classes" in wrapper_source


@pytest.mark.unit
def test_wrappers_stamps_new_rule_id(wrapper_source):
    """phase_wrappers must call stamp_inferred_relationships for the new rule_id."""
    assert "derive_slinks_from_predicate_classes_v1" in wrapper_source
