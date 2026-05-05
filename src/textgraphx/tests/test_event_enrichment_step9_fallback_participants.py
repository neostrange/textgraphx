"""Tests for Step 9: add_precision_fallback_participants.

Verifies source structure and mock-based behaviour of the opt-in
head-token fallback participant linking method.

Guards verified:
- Core roles only (ARG0-ARG4)
- Non-provisional frame guard
- Canonical non-merged TEvent guard
- No competing PARTICIPANT guard (NOT EXISTS)
- Entity head-token alignment (start_tok ≤ head_idx ≤ end_tok  OR  ±1 tolerance)
- confidence = 0.55
- rule_id = 'precision_fallback_participant_v1'
- ON CREATE SET semantics (idempotent)
- Exception safety
- Opt-in: wired in __main__ but NOT in phase_wrappers by default

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

EEP_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"
)


@pytest.fixture(scope="module")
def eep_source() -> str:
    return EEP_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"{method_name!r} not found in source"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


@pytest.fixture(scope="module")
def method_src(eep_source):
    return _extract_method(eep_source, "add_precision_fallback_participants")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def add_precision_fallback_participants" in eep_source


# ---------------------------------------------------------------------------
# Core-role guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_guards_core_roles_only(method_src):
    assert "'ARG0'" in method_src
    assert "'ARG4'" in method_src


# ---------------------------------------------------------------------------
# Provisional frame guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_provisional_frame_guard(method_src):
    assert "provisional" in method_src


# ---------------------------------------------------------------------------
# Canonical event guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_merged_event_guard(method_src):
    assert "event.merged" in method_src or "merged, false)" in method_src


# ---------------------------------------------------------------------------
# No competing PARTICIPANT guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_competing_participant_guard(method_src):
    """Must use NOT EXISTS to skip events that already have a canonical link."""
    assert "NOT EXISTS" in method_src
    assert "PARTICIPANT" in method_src


# ---------------------------------------------------------------------------
# Head-token alignment
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_uses_head_token_alignment(method_src):
    assert "headTokenIndex" in method_src or "head_idx" in method_src


@pytest.mark.unit
def test_tolerance_1_present(method_src):
    assert "<= 1" in method_src


@pytest.mark.unit
def test_entity_label_matched(method_src):
    assert ":Entity" in method_src


# ---------------------------------------------------------------------------
# Provenance properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_confidence_is_0_55(method_src):
    assert "0.55" in method_src


@pytest.mark.unit
def test_rule_id_set(method_src):
    assert "precision_fallback_participant_v1" in method_src


@pytest.mark.unit
def test_sets_is_core_true(method_src):
    assert "is_core" in method_src


@pytest.mark.unit
def test_on_create_set_semantics(method_src):
    """Must use ON CREATE SET so the edge is idempotent."""
    assert "ON CREATE SET" in method_src


@pytest.mark.unit
def test_writes_event_participant_edge(method_src):
    assert "EVENT_PARTICIPANT" in method_src


# ---------------------------------------------------------------------------
# Exception safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_exception_safety(method_src):
    assert "except Exception" in method_src
    assert "return 0" in method_src


# ---------------------------------------------------------------------------
# Opt-in wiring: __main__ only, NOT phase_wrappers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    assert main_start != -1
    main_block = eep_source[main_start:]
    assert "add_precision_fallback_participants" in main_block


@pytest.mark.unit
def test_not_wired_in_phase_wrappers():
    wrappers_path = EEP_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "add_precision_fallback_participants" not in src, (
        "Step 9 is opt-in; it must NOT be wired into phase_wrappers "
        "until A/B evaluation confirms net gain."
    )


# ---------------------------------------------------------------------------
# Mock-based behaviour
# ---------------------------------------------------------------------------


def _make_phase(rows):
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = rows
    phase.graph = mock_graph
    return phase


@pytest.mark.unit
def test_returns_created_count():
    phase = _make_phase([{"created": 7}])
    result = phase.add_precision_fallback_participants()
    assert result == 7


@pytest.mark.unit
def test_returns_zero_when_no_rows():
    phase = _make_phase([])
    result = phase.add_precision_fallback_participants()
    assert result == 0


@pytest.mark.unit
def test_returns_zero_on_exception():
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.side_effect = RuntimeError("db down")
    phase.graph = mock_graph
    assert phase.add_precision_fallback_participants() == 0
