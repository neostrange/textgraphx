"""Phase-D regression tests for mode-aware assertion thresholds in wrappers."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_phase_wrappers_define_mode_threshold_helper():
    src = Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")

    assert "def _phase_thresholds_for_mode(phase_name: str):" in src
    assert "strict_modes" in src
    assert "review" in src and "testing" in src and "test" in src and "ci" in src
    assert "thresholds.max_tlink_consistency_violations = 0" in src


@pytest.mark.unit
def test_temporal_and_tlinks_assertions_use_mode_thresholds():
    src = Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")

    assert "thresholds=_phase_thresholds_for_mode(\"temporal\")" in src
    assert "thresholds=_phase_thresholds_for_mode(\"tlinks\")" in src
