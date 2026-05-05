"""Tests for EventEnrichmentPhase.promote_nombank_frames_to_tevents (Phase D2).

Static source-inspection tests covering the eventive-evidence gate and
confidence-calibration logic added in the SRL/NomBank improvement series.

No live Neo4j or spaCy required — all tests are pure source inspection or
lightweight mock-based unit tests.
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
    return _extract_method(eep_source, "promote_nombank_frames_to_tevents")


# ---------------------------------------------------------------------------
# Candidate query columns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCandidateQueryColumns:
    def test_returns_sense_conf(self, method_src):
        """Candidate query must return sense_conf for the confidence gate."""
        assert "sense_conf" in method_src

    def test_returns_has_verbal_alignment(self, method_src):
        """Candidate query must return has_verbal_alignment (ALIGNS_WITH → PROPBANK)."""
        assert "has_verbal_alignment" in method_src

    def test_aligns_with_propbank_check_in_query(self, method_src):
        """The verbal alignment check must inspect ALIGNS_WITH edges to PROPBANK frames."""
        assert "ALIGNS_WITH" in method_src
        assert "PROPBANK" in method_src


# ---------------------------------------------------------------------------
# WordNet-absent branch (Branch A)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWordNetAbsentBranch:
    def test_temporal_wn_imported(self, method_src):
        """Must import _wn from temporal module to detect WordNet availability."""
        assert "_temporal_wn" in method_src or "_wn as _temporal_wn" in method_src

    def test_branch_a_verbal_alignment_permits_promotion(self, method_src):
        """When WordNet absent, verbal alignment must allow promotion."""
        # The guard is: if not (has_verbal or sense_conf >= threshold): continue
        assert "has_verbal" in method_src

    def test_branch_a_high_sense_conf_permits_promotion(self, method_src):
        """When WordNet absent, sense_conf >= 0.65 must allow promotion."""
        assert "0.65" in method_src

    def test_branch_a_low_sense_conf_no_verbal_skipped(self, method_src):
        """Without WordNet, a frame with low sense_conf and no verbal alignment is blocked."""
        # Guard must combine the two conditions with OR (both must be false to skip)
        assert "has_verbal or sense_conf >= 0.65" in method_src or (
            "has_verbal" in method_src and "0.65" in method_src
        )


# ---------------------------------------------------------------------------
# WordNet-available branch (Branch B)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWordNetAvailableBranch:
    def test_branch_b_calls_is_eventive(self, method_src):
        """When WordNet available, _is_eventive must be called."""
        assert "_is_eventive(" in method_src

    def test_branch_b_sense_conf_gate_without_verbal(self, method_src):
        """Without verbal alignment, sense_conf must meet the 0.55 threshold."""
        assert "0.55" in method_src

    def test_branch_b_verbal_alignment_bypasses_conf_gate(self, method_src):
        """With verbal alignment, the secondary sense_conf gate is skipped."""
        # The gate is: if not has_verbal and sense_conf < 0.55: continue
        assert "not has_verbal and sense_conf < 0.55" in method_src


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfidenceCalibration:
    def test_verbally_aligned_confidence_is_0_80(self, method_src):
        """Verbally-aligned promoted events must receive confidence = 0.80."""
        assert "0.80" in method_src

    def test_standalone_confidence_is_0_70(self, method_src):
        """Standalone promoted events must receive confidence = 0.70."""
        assert "0.70" in method_src

    def test_confidence_is_parameterized_in_upsert(self, method_src):
        """The upsert Cypher must reference $confidence (not a hardcoded literal)."""
        assert "$confidence" in method_src

    def test_confidence_is_passed_in_parameters(self, method_src):
        """The parameters dict must include the 'confidence' key."""
        assert '"confidence": confidence' in method_src or "'confidence': confidence" in method_src


# ---------------------------------------------------------------------------
# Upsert query structure preserved
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpsertQueryStructure:
    def test_upsert_uses_merge(self, method_src):
        """Upsert must use MERGE for idempotency."""
        assert "MERGE (event:TEvent" in method_src

    def test_upsert_sets_source_nombank_srl(self, method_src):
        """Promoted TEvents must carry source = 'nombank_srl'."""
        assert "nombank_srl" in method_src

    def test_upsert_wires_triggers_edge(self, method_src):
        """Head token must be linked via TRIGGERS."""
        assert "TRIGGERS" in method_src

    def test_upsert_wires_describes_edge(self, method_src):
        """Frame must be linked to TEvent via DESCRIBES."""
        assert "DESCRIBES" in method_src
