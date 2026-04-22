"""CI-like integration scenario for quality report gating.

Validates the expected workflow in CI:
1. Produce a baseline report artifact.
2. Produce a current report artifact.
3. Run `check_quality_gate` to pass/fail the build.
"""

from __future__ import annotations

import json

import pytest

from textgraphx.tools.check_quality_gate import main as run_quality_gate


@pytest.mark.integration
def test_quality_gate_passes_when_current_meets_baseline(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"

    baseline.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 0,
                        "participation_in_mention_missing_count": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.82,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 0,
                        "participation_in_mention_missing_count": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    rc = run_quality_gate(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--tolerance",
            "0.0",
            "--max-participation-in-frame-missing-increase",
            "0",
            "--max-participation-in-mention-missing-increase",
            "0",
            "--max-participation-in-frame-missing",
            "0",
            "--max-participation-in-mention-missing",
            "0",
        ]
    )
    assert rc == 0


@pytest.mark.integration
def test_quality_gate_fails_when_regression_exceeds_tolerance(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"

    baseline.write_text(
        json.dumps(
            {
                "overall_quality": 0.85,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 0,
                        "participation_in_mention_missing_count": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 1,
                        "participation_in_mention_missing_count": 1,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    rc = run_quality_gate(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--tolerance",
            "0.02",
            "--max-participation-in-frame-missing-increase",
            "0",
            "--max-participation-in-mention-missing-increase",
            "0",
            "--max-participation-in-frame-missing",
            "0",
            "--max-participation-in-mention-missing",
            "0",
        ]
    )
    assert rc == 1
