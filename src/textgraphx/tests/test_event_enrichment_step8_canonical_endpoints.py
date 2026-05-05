"""Tests for Step 8: canonicalize_participant_endpoints method.

Verifies source structure and mock-based behaviour of the new
canonicalize_participant_endpoints method in EventEnrichmentPhase.

Ensures:
- Both PARTICIPANT and EVENT_PARTICIPANT edges are transferred
- Transfer only targets merged=true TEvents with a merged_into pointer
- canonical target is guarded merged=false
- confidence is scaled by 0.95
- transferred_from, rule_id, created_at are set ON CREATE
- Non-fatal exception handling per relationship type
- Returns total transferred count
- Correct ordering in __main__ and phase_wrappers

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock, call

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
def canon_src(eep_source):
    return _extract_method(eep_source, "canonicalize_participant_endpoints")


# ---------------------------------------------------------------------------
# Method existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def canonicalize_participant_endpoints" in eep_source


@pytest.mark.unit
def test_method_returns_int(canon_src):
    assert "return total_transferred" in canon_src


# ---------------------------------------------------------------------------
# Relationship types covered
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transfers_participant_edges(canon_src):
    assert ":PARTICIPANT" in canon_src


@pytest.mark.unit
def test_transfers_event_participant_edges(canon_src):
    assert ":EVENT_PARTICIPANT" in canon_src


# ---------------------------------------------------------------------------
# Merge semantics: only secondary events (merged=true)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_guards_on_secondary_merged_true(canon_src):
    assert "secondary.merged" in canon_src or "merged, false) = true" in canon_src


@pytest.mark.unit
def test_guards_merged_into_not_null(canon_src):
    assert "merged_into IS NOT NULL" in canon_src


@pytest.mark.unit
def test_canonical_guard_merged_false(canon_src):
    """Canonical target must also be guarded against already-merged nodes."""
    assert "canonical.merged" in canon_src or "coalesce(canonical" in canon_src


# ---------------------------------------------------------------------------
# ON CREATE / transferred_from properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sets_transferred_from(canon_src):
    assert "transferred_from" in canon_src


@pytest.mark.unit
def test_sets_rule_id(canon_src):
    assert "canonicalize_participant_endpoints_v1" in canon_src


@pytest.mark.unit
def test_sets_created_at(canon_src):
    assert "created_at" in canon_src


@pytest.mark.unit
def test_confidence_scaled_by_0_95(canon_src):
    assert "0.95" in canon_src


# ---------------------------------------------------------------------------
# Exception safety per relationship type
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_exception_safety_present(canon_src):
    """Must have exception handling so one failure doesn't abort both passes."""
    assert canon_src.count("except Exception") >= 1


# ---------------------------------------------------------------------------
# Wiring: __main__
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    assert main_start != -1
    main_block = eep_source[main_start:]
    assert "canonicalize_participant_endpoints" in main_block


@pytest.mark.unit
def test_wired_after_diagnostics_in_main(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    main_block = eep_source[main_start:]
    diag_pos = main_block.find("report_event_cluster_diagnostics")
    canon_pos = main_block.find("canonicalize_participant_endpoints")
    assert diag_pos != -1 and canon_pos != -1
    assert canon_pos > diag_pos, "canonicalize must follow report_event_cluster_diagnostics"


@pytest.mark.unit
def test_wired_before_add_core_participants_in_main(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    main_block = eep_source[main_start:]
    canon_pos = main_block.find("canonicalize_participant_endpoints")
    core_pos = main_block.find("add_core_participants_to_event")
    assert canon_pos != -1 and core_pos != -1
    assert canon_pos < core_pos, "canonicalize must precede add_core_participants_to_event"


# ---------------------------------------------------------------------------
# Wiring: phase_wrappers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_phase_wrappers():
    wrappers_path = EEP_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "canonicalize_participant_endpoints" in src


@pytest.mark.unit
def test_phase_wrappers_stamp_rule_id():
    wrappers_path = EEP_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "canonicalize_participant_endpoints_v1" in src


# ---------------------------------------------------------------------------
# Mock-based behaviour
# ---------------------------------------------------------------------------


def _make_phase(side_effects):
    """Build a minimal mock whose graph.run() cycles through side_effects."""
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_run = MagicMock()
    mock_run.data.side_effect = side_effects
    mock_graph.run.return_value = mock_run
    phase.graph = mock_graph
    return phase


@pytest.mark.unit
def test_returns_total_transferred_sum():
    phase = _make_phase([
        [{"transferred": 5}],   # PARTICIPANT
        [{"transferred": 3}],   # EVENT_PARTICIPANT
    ])
    result = phase.canonicalize_participant_endpoints()
    assert result == 8


@pytest.mark.unit
def test_returns_zero_when_no_rows():
    phase = _make_phase([[], []])
    result = phase.canonicalize_participant_endpoints()
    assert result == 0


@pytest.mark.unit
def test_tolerates_first_pass_exception():
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.side_effect = [
        RuntimeError("PARTICIPANT fail"),
        MagicMock(**{"data.return_value": [{"transferred": 4}]}),
    ]
    phase.graph = mock_graph
    # Should not raise; second pass still completes
    result = phase.canonicalize_participant_endpoints()
    assert result == 4


@pytest.mark.unit
def test_tolerates_both_passes_exception():
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.side_effect = RuntimeError("all failed")
    phase.graph = mock_graph
    result = phase.canonicalize_participant_endpoints()
    assert result == 0


@pytest.mark.unit
def test_issues_two_graph_run_calls():
    phase = _make_phase([
        [{"transferred": 2}],
        [{"transferred": 1}],
    ])
    phase.canonicalize_participant_endpoints()
    assert phase.graph.run.call_count == 2
