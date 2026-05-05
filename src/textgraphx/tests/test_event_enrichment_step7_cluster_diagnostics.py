"""Tests for Step 7: report_event_cluster_diagnostics method.

Verifies source structure and mock-based behaviour of the new
report_event_cluster_diagnostics method in EventEnrichmentPhase.

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
def diag_src(eep_source):
    return _extract_method(eep_source, "report_event_cluster_diagnostics")


# ---------------------------------------------------------------------------
# Method existence and return type
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(eep_source):
    assert "def report_event_cluster_diagnostics" in eep_source


@pytest.mark.unit
def test_method_returns_dict(diag_src):
    """Method must have dict-typed return paths."""
    assert "return diag" in diag_src or "return {}" in diag_src


# ---------------------------------------------------------------------------
# Query covers expected diagnostic keys
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_query_counts_clusters_formed(diag_src):
    assert "clusters_formed" in diag_src


@pytest.mark.unit
def test_query_counts_sense_conflicts(diag_src):
    assert "sense_conflicts" in diag_src


@pytest.mark.unit
def test_query_counts_em_redirected(diag_src):
    assert "em_redirected" in diag_src


@pytest.mark.unit
def test_query_counts_events_merged(diag_src):
    assert "events_merged" in diag_src


@pytest.mark.unit
def test_query_counts_events_unmerged(diag_src):
    assert "events_unmerged" in diag_src


@pytest.mark.unit
def test_query_counts_lv_merges(diag_src):
    assert "lv_merges" in diag_src


# ---------------------------------------------------------------------------
# Query references correct graph signals
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_query_checks_aligns_with(diag_src):
    assert "ALIGNS_WITH" in diag_src


@pytest.mark.unit
def test_query_checks_sense_conflict_property(diag_src):
    assert "sense_conflict" in diag_src


@pytest.mark.unit
def test_query_checks_provisional(diag_src):
    assert "provisional" in diag_src


@pytest.mark.unit
def test_query_checks_merged_by_lv(diag_src):
    assert "light_verb_canonicalization" in diag_src


@pytest.mark.unit
def test_query_checks_em_refers_to_source(diag_src):
    """Must distinguish merge sources (aligns_with_merge / light_verb_canonicalization)."""
    assert "aligns_with_merge" in diag_src


# ---------------------------------------------------------------------------
# Exception safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_returns_empty_dict_on_exception(diag_src):
    """Must catch exceptions and return {} instead of propagating."""
    assert "except Exception" in diag_src
    assert "return {}" in diag_src


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_logs_all_keys(diag_src):
    """INFO log must mention all six diagnostic keys."""
    for key in ("clusters_formed", "sense_conflicts", "em_redirected",
                "events_merged", "events_unmerged", "lv_merges"):
        assert key in diag_src


# ---------------------------------------------------------------------------
# Wiring: __main__ and phase_wrappers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    assert main_start != -1
    main_block = eep_source[main_start:]
    assert "report_event_cluster_diagnostics" in main_block


@pytest.mark.unit
def test_wired_after_merge_aligns_with_in_main(eep_source):
    main_start = eep_source.find("if __name__ == '__main__':")
    main_block = eep_source[main_start:]
    merge_pos = main_block.find("merge_aligns_with_event_clusters")
    diag_pos = main_block.find("report_event_cluster_diagnostics")
    assert merge_pos != -1 and diag_pos != -1
    assert diag_pos > merge_pos, "diagnostics must follow merge_aligns_with_event_clusters"


@pytest.mark.unit
def test_wired_in_phase_wrappers():
    wrappers_path = EEP_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "report_event_cluster_diagnostics" in src


# ---------------------------------------------------------------------------
# Mock-based behaviour
# ---------------------------------------------------------------------------


def _make_phase(rows):
    """Build a minimal EventEnrichmentPhase mock whose graph.run().data() returns rows."""
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = rows
    phase.graph = mock_graph
    return phase


@pytest.mark.unit
def test_returns_dict_from_graph():
    phase = _make_phase([{
        "clusters_formed": 3,
        "sense_conflicts": 1,
        "em_redirected": 2,
        "events_merged": 4,
        "events_unmerged": 10,
        "lv_merges": 1,
    }])
    result = phase.report_event_cluster_diagnostics()
    assert isinstance(result, dict)
    assert result["clusters_formed"] == 3
    assert result["events_unmerged"] == 10


@pytest.mark.unit
def test_returns_empty_dict_when_no_rows():
    phase = _make_phase([])
    result = phase.report_event_cluster_diagnostics()
    assert result == {}


@pytest.mark.unit
def test_returns_empty_dict_on_db_exception():
    from textgraphx.pipeline.phases.event_enrichment import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    mock_graph = MagicMock()
    mock_graph.run.side_effect = RuntimeError("db offline")
    phase.graph = mock_graph
    result = phase.report_event_cluster_diagnostics()
    assert result == {}
