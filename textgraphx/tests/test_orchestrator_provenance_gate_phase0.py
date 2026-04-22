"""Phase-0 tests for strict provenance gating in orchestrator."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_strict_gate_fails_on_provenance_violations(tmp_path):
    from textgraphx.orchestration.orchestrator import PipelineOrchestrator

    fake_cfg = MagicMock()
    fake_cfg.runtime.mode = "testing"
    fake_cfg.runtime.strict_transition_gate = True

    with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
        orchestrator = PipelineOrchestrator(directory=str(tmp_path))

    with patch.object(
        orchestrator,
        "_run_ingestion",
        return_value={"documents_processed": 1, "assertions_passed": True, "provenance_violations": 3},
    ):
        with pytest.raises(RuntimeError, match="provenance contract violations"):
            orchestrator.run_selected(["ingestion"])


@pytest.mark.unit
def test_non_strict_mode_allows_provenance_violations(tmp_path):
    from textgraphx.orchestration.orchestrator import PipelineOrchestrator

    fake_cfg = MagicMock()
    fake_cfg.runtime.mode = "production"
    fake_cfg.runtime.strict_transition_gate = False

    with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
        orchestrator = PipelineOrchestrator(directory=str(tmp_path))

    with patch.object(
        orchestrator,
        "_run_ingestion",
        return_value={"documents_processed": 1, "assertions_passed": True, "provenance_violations": 2},
    ):
        orchestrator.run_selected(["ingestion"])

    assert orchestrator.summary.success_count == 1
    assert orchestrator.summary.failed_count == 0
