"""Tests for reusable KG quality evaluation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from textgraphx.kg_quality_evaluation import (
    compare_reports,
    compute_semantic_metrics,
    compute_structural_metrics,
    compute_temporal_metrics,
    generate_quality_report,
    identify_regression,
    load_quality_report,
    overall_quality_from_report,
    runtime_total_from_report,
)


pytestmark = [pytest.mark.unit]


class _FakeSuite:
    def overall_quality(self) -> float:
        return 0.82

    def quality_scores(self):
        return {
            "mention_layer": 0.80,
            "edge_semantics": 0.84,
            "phase_assertions": 0.81,
        }

    def conclusiveness(self):
        return False, ["phase_assertions: endpoint drift"]


def _sample_runtime_diagnostics():
    return {
        "phase_execution_summary": [
            {
                "phase": "temporal",
                "execution_count": 2,
                "documents_processed": 5,
                "duration_seconds": 1.25,
            },
            {
                "phase": "event_enrichment",
                "execution_count": 2,
                "documents_processed": 5,
                "duration_seconds": 0.75,
            },
        ],
        "totals": {
            "assertion_violation_count": 1,
            "referential_integrity_violation_count": 2,
            "identity_contract_violation_count": 0,
            "glink_count": 3,
            "endpoint_violation_count": 2,
            "provenance_violation_count": 1,
            "factuality_attribution_violation_count": 0,
            "factuality_alignment_violation_count": 1,
            "entity_state_coverage_ratio": 0.70,
            "entity_specificity_coverage_ratio": 0.90,
            "event_external_ref_coverage_ratio": 0.75,
            "factuality_coverage_ratio": 0.80,
            "tlink_conflict_count": 2,
            "tlink_anchor_inconsistent_count": 1,
            "tlink_anchor_self_link_count": 0,
            "tlink_anchor_endpoint_violation_count": 1,
            "tlink_anchor_filter_suppressed_count": 2,
            "tlink_missing_anchor_metadata_count": 1,
        },
    }


def test_compute_metrics_extracts_counts_and_scores():
    runtime_diagnostics = _sample_runtime_diagnostics()

    structural = compute_structural_metrics(runtime_diagnostics=runtime_diagnostics)
    semantic = compute_semantic_metrics(runtime_diagnostics=runtime_diagnostics)
    temporal = compute_temporal_metrics(runtime_diagnostics=runtime_diagnostics)

    assert structural["phase_execution_count"] == 4
    assert structural["documents_processed"] == 10
    assert structural["structural_health_score"] < 1.0

    assert semantic["endpoint_violation_count"] == 2
    assert semantic["coverage_score"] == pytest.approx(0.7875)
    assert semantic["semantic_compliance_score"] < semantic["coverage_score"]

    assert temporal["tlink_conflict_count"] == 2
    assert temporal["temporal_issue_count"] == 7
    assert temporal["temporal_consistency_score"] < 1.0


def test_generate_quality_report_uses_suite_and_emits_recommendations():
    report = generate_quality_report(
        runtime_diagnostics=_sample_runtime_diagnostics(),
        evaluation_suite=_FakeSuite(),
        document_id="doc-7",
    )

    assert report["document_id"] == "doc-7"
    assert report["overall_quality"] == pytest.approx(0.82)
    assert report["quality_tier"] == "ACCEPTABLE"
    assert report["phase_quality_scores"]["mention_layer"] == pytest.approx(0.80)
    assert report["conclusive"] is False
    assert report["runtime_diagnostics"]["totals"]["glink_count"] == 3
    assert report["glink_count"] == 3
    assert report["warnings"]
    assert any("Temporal consistency issues" in warning for warning in report["warnings"])
    assert any("TLINK conflicts" in rec for rec in report["recommendations"])


def test_compare_reports_and_identify_regression_surface_deltas():
    baseline = {
        "overall_quality": 0.88,
        "phase_quality_scores": {"mention_layer": 0.90, "edge_semantics": 0.86},
        "structural_metrics": {"structural_health_score": 0.95},
        "semantic_metrics": {"semantic_compliance_score": 0.84},
        "temporal_metrics": {"temporal_consistency_score": 0.86},
    }
    current = {
        "overall_quality": 0.81,
        "phase_quality_scores": {"mention_layer": 0.83, "edge_semantics": 0.84},
        "structural_metrics": {"structural_health_score": 0.94},
        "semantic_metrics": {"semantic_compliance_score": 0.79},
        "temporal_metrics": {"temporal_consistency_score": 0.70},
    }

    comparison = compare_reports(baseline, current, tolerance=0.01)
    is_regression, reasons = identify_regression(baseline, current, tolerance=0.01)

    assert comparison["is_regression"] is True
    assert comparison["overall_quality_delta"] == pytest.approx(-0.07)
    assert comparison["regressed_sections"] == ["semantic", "temporal"]
    assert comparison["phase_deltas"]["mention_layer"] == pytest.approx(-0.07)
    assert is_regression is True
    assert any("Overall quality regressed" in reason for reason in reasons)
    assert any("Phase 'mention_layer' regressed" in reason for reason in reasons)


def test_report_loading_and_total_extraction_support_current_shapes(tmp_path):
    report_path = tmp_path / "report.json"
    payload = {
        "overall_quality": 0.91,
        "runtime_diagnostics": {
            "totals": {
                "tlink_anchor_inconsistent_count": 2,
            }
        },
    }
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_quality_report(report_path)
    assert loaded == payload
    assert overall_quality_from_report(loaded) == pytest.approx(0.91)
    assert runtime_total_from_report(loaded, "tlink_anchor_inconsistent_count") == 2