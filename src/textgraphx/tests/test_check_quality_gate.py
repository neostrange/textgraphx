"""Tests for textgraphx.tools.check_quality_gate."""

from pathlib import Path
import json

import pytest

from textgraphx.tools.check_quality_gate import _overall_quality, _runtime_total, main


# ---------------------------------------------------------------------------
# _overall_quality extraction
# ---------------------------------------------------------------------------

def test_overall_quality_top_level():
    assert _overall_quality({"overall_quality": 0.85}) == pytest.approx(0.85)


def test_overall_quality_nested_suite():
    report = {"suite": {"overall_quality": 0.72}}
    assert _overall_quality(report) == pytest.approx(0.72)


def test_overall_quality_missing_key():
    with pytest.raises(KeyError, match="overall_quality"):
        _overall_quality({"phase_reports": []})


def test_runtime_total_from_nested_totals():
    report = {
        "runtime_diagnostics": {
            "totals": {
                "tlink_anchor_inconsistent_count": 2,
            }
        }
    }
    assert _runtime_total(report, "tlink_anchor_inconsistent_count") == 2


def test_runtime_total_from_summary_shape():
    report = {
        "tlink_missing_anchor_metadata_count": 1,
    }
    assert _runtime_total(report, "tlink_missing_anchor_metadata_count") == 1


# ---------------------------------------------------------------------------
# main() exit codes
# ---------------------------------------------------------------------------

def _write_report(path: Path, quality: float) -> None:
    path.write_text(json.dumps({"overall_quality": quality}))


def test_gate_passes_when_current_meets_baseline(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.80)
    _write_report(current, 0.80)
    assert main(["--baseline", str(baseline), "--current", str(current)]) == 0


def test_gate_passes_current_above_baseline(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.70)
    _write_report(current, 0.85)
    assert main(["--baseline", str(baseline), "--current", str(current)]) == 0


def test_gate_fails_on_regression(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.80)
    _write_report(current, 0.70)
    assert main(["--baseline", str(baseline), "--current", str(current)]) == 1


def test_gate_passes_within_tolerance(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.80)
    _write_report(current, 0.79)  # 0.01 regression; tolerance 0.02 should pass
    assert main([
        "--baseline", str(baseline),
        "--current", str(current),
        "--tolerance", "0.02",
    ]) == 0


def test_gate_fails_beyond_tolerance(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.80)
    _write_report(current, 0.77)  # 0.03 regression; tolerance 0.02 => fail
    assert main([
        "--baseline", str(baseline),
        "--current", str(current),
        "--tolerance", "0.02",
    ]) == 1


def test_gate_returns_2_for_missing_file(tmp_path):
    baseline = tmp_path / "baseline.json"
    _write_report(baseline, 0.80)
    result = main([
        "--baseline", str(baseline),
        "--current", str(tmp_path / "nonexistent.json"),
    ])
    assert result == 2


def test_gate_verbose_flag_does_not_change_exit_code(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    _write_report(baseline, 0.80)
    _write_report(current, 0.82)
    rc = main(["--baseline", str(baseline), "--current", str(current), "--verbose"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "delta=+" in out


def test_gate_fails_on_tlink_anchor_inconsistent_increase(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "tlink_anchor_inconsistent_count": 1,
                    }
                },
            }
        )
    )
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "tlink_anchor_inconsistent_count": 3,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-tlink-anchor-inconsistent-increase",
            "0",
        ]
    )
    assert rc == 1


def test_gate_passes_when_tlink_anchor_inconsistent_increase_within_limit(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80, "tlink_anchor_inconsistent_count": 2}))
    current.write_text(json.dumps({"overall_quality": 0.80, "tlink_anchor_inconsistent_count": 3}))

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-tlink-anchor-inconsistent-increase",
            "1",
        ]
    )
    assert rc == 0


def test_gate_fails_on_tlink_missing_anchor_metadata_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "tlink_missing_anchor_metadata_count": 2,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-tlink-missing-anchor-metadata",
            "0",
        ]
    )
    assert rc == 1


def test_gate_fails_on_participation_in_frame_missing_increase(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "overall_quality": 0.90,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 1,
                    }
                },
            }
        )
    )
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.90,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 3,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-participation-in-frame-missing-increase",
            "0",
        ]
    )
    assert rc == 1


def test_gate_passes_when_participation_in_mention_missing_increase_within_limit(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80, "participation_in_mention_missing_count": 4}))
    current.write_text(json.dumps({"overall_quality": 0.80, "participation_in_mention_missing_count": 5}))

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-participation-in-mention-missing-increase",
            "1",
        ]
    )
    assert rc == 0


def test_gate_fails_on_participation_in_frame_missing_absolute_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_frame_missing_count": 2,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-participation-in-frame-missing",
            "0",
        ]
    )
    assert rc == 1


def test_gate_fails_on_participation_in_mention_missing_absolute_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "participation_in_mention_missing_count": 1,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-participation-in-mention-missing",
            "0",
        ]
    )
    assert rc == 1


def test_gate_fails_on_timexmention_missing_doc_id_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "timexmention_missing_doc_id_count": 1,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-timexmention-missing-doc-id",
            "0",
        ]
    )
    assert rc == 1


def test_gate_fails_on_timexmention_broken_refers_to_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "timexmention_broken_refers_to_count": 2,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-timexmention-broken-refers-to",
            "0",
        ]
    )
    assert rc == 1


def test_gate_fails_on_dct_timexmention_exemption_cap(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"overall_quality": 0.80}))
    current.write_text(
        json.dumps(
            {
                "overall_quality": 0.80,
                "runtime_diagnostics": {
                    "totals": {
                        "dct_timexmention_count": 1,
                    }
                },
            }
        )
    )

    rc = main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--max-dct-timexmention-count",
            "0",
        ]
    )
    assert rc == 1
