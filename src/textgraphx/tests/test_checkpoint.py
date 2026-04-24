"""Tests for checkpoint persistence and resume planning."""

from pathlib import Path

import pytest

from textgraphx.checkpoint import CheckpointManager
from textgraphx.orchestration.checkpoint import CheckpointManager as CanonicalCheckpointManager


pytestmark = [pytest.mark.unit]


def test_root_checkpoint_wrapper_reexports_canonical_manager():
    assert CheckpointManager is CanonicalCheckpointManager


def test_save_and_load_checkpoint(tmp_path):
    manager = CheckpointManager(base_dir=str(tmp_path / "checkpoints"))
    manager.save_checkpoint(
        doc_id="12345",
        phase_name="TemporalPhase",
        node_counts={"TEvent": 2},
        edge_counts={"TRIGGERS": 2},
        phase_markers=["ingestion", "refinement", "temporal"],
        properties_snapshot={"assertions_passed": True},
    )

    loaded = manager.load_checkpoint("12345", "TemporalPhase")
    assert loaded is not None
    assert loaded["doc_id"] == "12345"
    assert loaded["phase"] == "TemporalPhase"
    assert loaded["node_counts"]["TEvent"] == 2


def test_checkpoint_file_location_pattern(tmp_path):
    manager = CheckpointManager(base_dir=str(tmp_path / "out" / "checkpoints"))
    path = manager.save_checkpoint(doc_id="doc-1", phase_name="temporal")

    expected_suffix = Path("doc-1") / "temporal.json"
    assert path.exists()
    assert str(path).endswith(str(expected_suffix))


def test_validate_checkpoint_integrity_thresholds(tmp_path):
    manager = CheckpointManager(base_dir=str(tmp_path / "checkpoints"))
    payload = {
        "doc_id": "abc",
        "phase": "TemporalPhase",
        "node_counts": {"TEvent": 2},
        "edge_counts": {"TRIGGERS": 1},
    }

    assert manager.validate_checkpoint(
        payload,
        expected_doc_id="abc",
        allowed_phases=["TemporalPhase", "EventEnrichmentPhase"],
        min_node_counts={"TEvent": 1},
        min_edge_counts={"TRIGGERS": 1},
    )
    assert not manager.validate_checkpoint(
        payload,
        expected_doc_id="wrong",
    )


def test_resume_skips_completed_phases(tmp_path):
    manager = CheckpointManager(base_dir=str(tmp_path / "checkpoints"))
    phase_order = ["ingestion", "refinement", "temporal", "event_enrichment", "tlinks"]

    manager.save_checkpoint("doc-x", "ingestion")
    manager.save_checkpoint("doc-x", "refinement")

    summary = manager.resume_from_checkpoint("doc-x", phase_order)
    assert summary.completed_phases == ["ingestion", "refinement"]
    assert summary.remaining_phases == ["temporal", "event_enrichment", "tlinks"]
    assert summary.resume_from_phase == "temporal"
