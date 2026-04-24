"""Reusable KG quality evaluation helpers.

This module provides a small programmatic layer over the existing evaluation,
diagnostics, and regression-reporting infrastructure so callers do not need to
reconstruct quality summaries from CLI output.
"""

from __future__ import annotations

from math import isclose
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from textgraphx.evaluation.diagnostics import get_runtime_metrics
from textgraphx.time_utils import utc_iso_now as _canonical_utc_iso_now


def _utc_iso_now() -> str:
    return _canonical_utc_iso_now().replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _copy_mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _quality_tier(score: float) -> str:
    if score >= 0.90:
        return "PRODUCTION_READY"
    if score >= 0.80:
        return "ACCEPTABLE"
    if score >= 0.70:
        return "NEEDS_WORK"
    return "RESEARCH_PHASE"


def load_quality_report(path: str | Path) -> Dict[str, Any]:
    """Load a JSON quality report from disk."""
    report_path = Path(path)
    with report_path.open() as fh:
        return json.load(fh)


def overall_quality_from_report(report: Mapping[str, Any]) -> float:
    """Extract overall_quality from supported report shapes."""
    if "overall_quality" in report:
        return _safe_float(report.get("overall_quality"))
    for key in ("suite", "report", "result"):
        nested = report.get(key)
        if isinstance(nested, Mapping) and "overall_quality" in nested:
            return _safe_float(nested.get("overall_quality"))
    raise KeyError(
        "Cannot locate 'overall_quality' in report. "
        "Run evaluate_kg_quality with --json to produce a compatible report."
    )


def runtime_total_from_report(report: Mapping[str, Any], key: str, default: int = 0) -> int:
    """Extract a runtime diagnostics total from supported report shapes."""
    if key in report:
        return _safe_int(report.get(key, default))
    diagnostics = report.get("runtime_diagnostics", {})
    if isinstance(diagnostics, Mapping):
        totals = diagnostics.get("totals", {})
        if isinstance(totals, Mapping):
            return _safe_int(totals.get(key, default))
    totals = report.get("diagnostics_totals", {})
    if isinstance(totals, Mapping):
        return _safe_int(totals.get(key, default))
    return default


def _runtime_diagnostics_payload(
    graph: Any = None,
    runtime_diagnostics: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    if runtime_diagnostics is not None:
        return dict(runtime_diagnostics)
    if graph is None:
        return {}
    payload = get_runtime_metrics(graph)
    return payload if isinstance(payload, dict) else {}


def _coverage_average(values: Sequence[float]) -> float:
    usable = [max(0.0, min(1.0, _safe_float(value))) for value in values]
    if not usable:
        return 0.0
    return sum(usable) / len(usable)


def _penalized_score(base_score: float, penalty_count: int, smoothing: float) -> float:
    score = max(0.0, min(1.0, _safe_float(base_score)))
    penalty = float(max(0, penalty_count)) / float(max(1.0, smoothing + penalty_count))
    return max(0.0, min(1.0, score - penalty))


def _is_regression_delta(delta: float, tolerance: float) -> bool:
    threshold = -abs(tolerance)
    return delta < threshold and not isclose(delta, threshold, abs_tol=1e-12)


def _is_improvement_delta(delta: float, tolerance: float) -> bool:
    threshold = abs(tolerance)
    return delta > threshold and not isclose(delta, threshold, abs_tol=1e-12)


def compute_structural_metrics(
    graph: Any = None,
    runtime_diagnostics: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute structural health metrics from runtime diagnostics."""
    diagnostics = _runtime_diagnostics_payload(graph=graph, runtime_diagnostics=runtime_diagnostics)
    phase_summary = diagnostics.get("phase_execution_summary", [])
    totals = diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {}

    execution_count = sum(_safe_int(row.get("execution_count")) for row in phase_summary)
    documents_processed = sum(_safe_int(row.get("documents_processed")) for row in phase_summary)
    duration_seconds = sum(_safe_float(row.get("duration_seconds")) for row in phase_summary)
    assertion_violation_count = _safe_int(totals.get("assertion_violation_count"))
    referential_integrity_violation_count = _safe_int(totals.get("referential_integrity_violation_count"))
    identity_contract_violation_count = _safe_int(totals.get("identity_contract_violation_count"))
    glink_count = _safe_int(totals.get("glink_count"))

    structural_issue_count = (
        assertion_violation_count
        + referential_integrity_violation_count
        + identity_contract_violation_count
    )
    smoothing = max(10.0, float(execution_count + documents_processed + glink_count))
    structural_health_score = _penalized_score(1.0, structural_issue_count, smoothing)

    return {
        "phase_execution_count": execution_count,
        "documents_processed": documents_processed,
        "duration_seconds": duration_seconds,
        "assertion_violation_count": assertion_violation_count,
        "referential_integrity_violation_count": referential_integrity_violation_count,
        "identity_contract_violation_count": identity_contract_violation_count,
        "glink_count": glink_count,
        "structural_issue_count": structural_issue_count,
        "structural_health_score": structural_health_score,
    }


def compute_semantic_metrics(
    graph: Any = None,
    runtime_diagnostics: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute semantic compliance metrics from runtime diagnostics."""
    diagnostics = _runtime_diagnostics_payload(graph=graph, runtime_diagnostics=runtime_diagnostics)
    totals = diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {}

    endpoint_violation_count = _safe_int(totals.get("endpoint_violation_count"))
    provenance_violation_count = _safe_int(totals.get("provenance_violation_count"))
    factuality_attribution_violation_count = _safe_int(totals.get("factuality_attribution_violation_count"))
    factuality_alignment_violation_count = _safe_int(totals.get("factuality_alignment_violation_count"))
    entity_state_coverage_ratio = _safe_float(totals.get("entity_state_coverage_ratio"))
    entity_specificity_coverage_ratio = _safe_float(totals.get("entity_specificity_coverage_ratio"))
    event_external_ref_coverage_ratio = _safe_float(totals.get("event_external_ref_coverage_ratio"))
    factuality_coverage_ratio = _safe_float(totals.get("factuality_coverage_ratio"))

    coverage_score = _coverage_average(
        [
            entity_state_coverage_ratio,
            entity_specificity_coverage_ratio,
            event_external_ref_coverage_ratio,
            factuality_coverage_ratio,
        ]
    )
    semantic_issue_count = (
        endpoint_violation_count
        + provenance_violation_count
        + factuality_attribution_violation_count
        + factuality_alignment_violation_count
    )
    semantic_compliance_score = _penalized_score(coverage_score, semantic_issue_count, 25.0)

    return {
        "endpoint_violation_count": endpoint_violation_count,
        "provenance_violation_count": provenance_violation_count,
        "factuality_attribution_violation_count": factuality_attribution_violation_count,
        "factuality_alignment_violation_count": factuality_alignment_violation_count,
        "entity_state_coverage_ratio": entity_state_coverage_ratio,
        "entity_specificity_coverage_ratio": entity_specificity_coverage_ratio,
        "event_external_ref_coverage_ratio": event_external_ref_coverage_ratio,
        "factuality_coverage_ratio": factuality_coverage_ratio,
        "semantic_issue_count": semantic_issue_count,
        "coverage_score": coverage_score,
        "semantic_compliance_score": semantic_compliance_score,
    }


def compute_temporal_metrics(
    graph: Any = None,
    runtime_diagnostics: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compute temporal consistency metrics from runtime diagnostics."""
    diagnostics = _runtime_diagnostics_payload(graph=graph, runtime_diagnostics=runtime_diagnostics)
    totals = diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {}

    tlink_conflict_count = _safe_int(totals.get("tlink_conflict_count"))
    tlink_anchor_inconsistent_count = _safe_int(totals.get("tlink_anchor_inconsistent_count"))
    tlink_anchor_self_link_count = _safe_int(totals.get("tlink_anchor_self_link_count"))
    tlink_anchor_endpoint_violation_count = _safe_int(totals.get("tlink_anchor_endpoint_violation_count"))
    tlink_anchor_filter_suppressed_count = _safe_int(totals.get("tlink_anchor_filter_suppressed_count"))
    tlink_missing_anchor_metadata_count = _safe_int(totals.get("tlink_missing_anchor_metadata_count"))
    tlink_reciprocal_cycle_count = _safe_int(totals.get("tlink_reciprocal_cycle_count"))
    isolated_temporal_anchor_count = _safe_int(totals.get("isolated_temporal_anchor_count"))
    documents_with_temporal_connectivity_gaps_count = _safe_int(
        totals.get("documents_with_temporal_connectivity_gaps_count")
    )
    documents_without_temporal_tlinks_count = _safe_int(
        totals.get("documents_without_temporal_tlinks_count")
    )

    temporal_issue_count = (
        tlink_conflict_count
        + tlink_anchor_inconsistent_count
        + tlink_anchor_self_link_count
        + tlink_anchor_endpoint_violation_count
        + tlink_anchor_filter_suppressed_count
        + tlink_missing_anchor_metadata_count
        + tlink_reciprocal_cycle_count
        + isolated_temporal_anchor_count
        + documents_with_temporal_connectivity_gaps_count
        + documents_without_temporal_tlinks_count
    )
    temporal_consistency_score = _penalized_score(1.0, temporal_issue_count, 40.0)

    return {
        "tlink_conflict_count": tlink_conflict_count,
        "tlink_anchor_inconsistent_count": tlink_anchor_inconsistent_count,
        "tlink_anchor_self_link_count": tlink_anchor_self_link_count,
        "tlink_anchor_endpoint_violation_count": tlink_anchor_endpoint_violation_count,
        "tlink_anchor_filter_suppressed_count": tlink_anchor_filter_suppressed_count,
        "tlink_missing_anchor_metadata_count": tlink_missing_anchor_metadata_count,
        "tlink_reciprocal_cycle_count": tlink_reciprocal_cycle_count,
        "isolated_temporal_anchor_count": isolated_temporal_anchor_count,
        "documents_with_temporal_connectivity_gaps_count": documents_with_temporal_connectivity_gaps_count,
        "documents_without_temporal_tlinks_count": documents_without_temporal_tlinks_count,
        "temporal_issue_count": temporal_issue_count,
        "temporal_consistency_score": temporal_consistency_score,
    }


def _report_quality_scores(report: Any) -> Dict[str, float]:
    if report is None:
        return {}
    quality_scores = getattr(report, "quality_scores", None)
    if callable(quality_scores):
        scores = quality_scores()
        if isinstance(scores, dict):
            return {str(key): _safe_float(value) for key, value in scores.items()}
    if isinstance(report, Mapping):
        scores = report.get("phase_quality_scores", {})
        if isinstance(scores, Mapping):
            return {str(key): _safe_float(value) for key, value in scores.items()}
    return {}


def _report_overall_quality(report: Any) -> float:
    if report is None:
        return 0.0
    overall_quality = getattr(report, "overall_quality", None)
    if callable(overall_quality):
        return _safe_float(overall_quality())
    if isinstance(report, Mapping):
        return _safe_float(report.get("overall_quality"))
    return 0.0


def _report_conclusiveness(report: Any) -> tuple[bool, list[str]]:
    conclusiveness = getattr(report, "conclusiveness", None)
    if callable(conclusiveness):
        result = conclusiveness()
        if isinstance(result, tuple) and len(result) == 2:
            return bool(result[0]), list(result[1])
    if isinstance(report, Mapping):
        return bool(report.get("conclusive", True)), list(report.get("reasons", []))
    return True, []


def _build_warnings_and_recommendations(
    structural_metrics: Mapping[str, Any],
    semantic_metrics: Mapping[str, Any],
    temporal_metrics: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    recommendations: list[str] = []

    if _safe_int(structural_metrics.get("structural_issue_count")) > 0:
        warnings.append(
            "Structural contract drift detected in phase assertions or canonical identity chains."
        )
        recommendations.append(
            "Inspect phase assertions, referential chains, and identity-contract violations before widening feature scope."
        )

    if _safe_float(semantic_metrics.get("entity_state_coverage_ratio")) < 0.80:
        warnings.append("Entity state coverage is below the 0.80 target.")
        recommendations.append(
            "Increase entity-state enrichment coverage before depending on state-sensitive downstream reasoning."
        )

    if _safe_float(semantic_metrics.get("event_external_ref_coverage_ratio")) < 0.80:
        warnings.append("Event external-ref coverage is below the 0.80 target.")
        recommendations.append(
            "Review event enrichment and external-ref propagation for canonical TEvent nodes."
        )

    if _safe_int(temporal_metrics.get("temporal_issue_count")) > 0:
        warnings.append("Temporal consistency issues were detected in TLINK diagnostics.")
        recommendations.append(
            "Investigate TLINK conflicts, anchor inconsistencies, reciprocal cycles, and temporal connectivity gaps before shipping temporal features."
        )

    if not warnings:
        recommendations.append("No immediate quality regressions detected; continue with the next feature slice.")

    return warnings, recommendations


def _build_temporal_findings(
    diagnostics: Mapping[str, Any],
    temporal_metrics: Mapping[str, Any],
) -> Dict[str, Any]:
    cycle_rows = diagnostics.get("tlink_reciprocal_cycle_signals", []) if isinstance(diagnostics, Mapping) else []
    gap_rows = diagnostics.get("temporal_anchor_connectivity_gaps", []) if isinstance(diagnostics, Mapping) else []

    if not isinstance(cycle_rows, list):
        cycle_rows = []
    if not isinstance(gap_rows, list):
        gap_rows = []

    top_cycle = cycle_rows[0] if cycle_rows else {}
    top_gap = gap_rows[0] if gap_rows else {}
    docs_without_temporal_tlinks = [
        row.get("document_id")
        for row in gap_rows
        if int(row.get("connected_anchor_count", 0) or 0) == 0 and row.get("document_id") is not None
    ]

    return {
        "reciprocal_cycle_count": _safe_int(temporal_metrics.get("tlink_reciprocal_cycle_count")),
        "isolated_temporal_anchor_count": _safe_int(temporal_metrics.get("isolated_temporal_anchor_count")),
        "documents_with_connectivity_gaps_count": _safe_int(
            temporal_metrics.get("documents_with_temporal_connectivity_gaps_count")
        ),
        "documents_without_temporal_tlinks_count": _safe_int(
            temporal_metrics.get("documents_without_temporal_tlinks_count")
        ),
        "top_reciprocal_cycle_signal": {
            "document_id": top_cycle.get("document_id"),
            "rel_type": top_cycle.get("rel_type"),
            "cycle_count": _safe_int(top_cycle.get("cycle_count")),
        },
        "top_connectivity_gap": {
            "document_id": top_gap.get("document_id"),
            "isolated_anchor_count": _safe_int(top_gap.get("isolated_anchor_count")),
            "connected_anchor_count": _safe_int(top_gap.get("connected_anchor_count")),
        },
        "documents_without_temporal_tlinks": docs_without_temporal_tlinks[:5],
    }


def generate_quality_report(
    *,
    graph: Any = None,
    runtime_diagnostics: Mapping[str, Any] | None = None,
    evaluation_suite: Any = None,
    document_id: Any = None,
    documents: int | None = None,
    evaluation_version: str = "1.0",
    timestamp: str | None = None,
    run_metadata: Mapping[str, Any] | None = None,
    capture_metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate a reusable quality report payload."""
    diagnostics = _runtime_diagnostics_payload(graph=graph, runtime_diagnostics=runtime_diagnostics)
    structural_metrics = compute_structural_metrics(runtime_diagnostics=diagnostics)
    semantic_metrics = compute_semantic_metrics(runtime_diagnostics=diagnostics)
    temporal_metrics = compute_temporal_metrics(runtime_diagnostics=diagnostics)

    metric_scores = {
        "structural": _safe_float(structural_metrics.get("structural_health_score")),
        "semantic": _safe_float(semantic_metrics.get("semantic_compliance_score")),
        "temporal": _safe_float(temporal_metrics.get("temporal_consistency_score")),
    }

    phase_quality_scores = _report_quality_scores(evaluation_suite)
    conclusive, reasons = _report_conclusiveness(evaluation_suite)
    overall_quality = _report_overall_quality(evaluation_suite)
    if overall_quality <= 0.0:
        overall_quality = sum(metric_scores.values()) / len(metric_scores)

    flat_runtime_totals = _copy_mapping(diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {})

    warnings, recommendations = _build_warnings_and_recommendations(
        structural_metrics=structural_metrics,
        semantic_metrics=semantic_metrics,
        temporal_metrics=temporal_metrics,
    )
    temporal_findings = _build_temporal_findings(diagnostics=diagnostics, temporal_metrics=temporal_metrics)
    report_run_metadata = _copy_mapping(run_metadata)
    report_capture_metadata = _copy_mapping(capture_metadata)

    report = {
        "timestamp": timestamp or _utc_iso_now(),
        "document_id": document_id,
        "documents": documents,
        "evaluation_version": evaluation_version,
        "run_metadata": report_run_metadata,
        "capture_metadata": report_capture_metadata,
        "overall_quality": overall_quality,
        "quality_tier": _quality_tier(overall_quality),
        "metric_scores": metric_scores,
        "structural_metrics": structural_metrics,
        "semantic_metrics": semantic_metrics,
        "temporal_metrics": temporal_metrics,
        "temporal_findings": temporal_findings,
        "phase_quality_scores": phase_quality_scores,
        "conclusive": conclusive,
        "reasons": reasons,
        "warnings": warnings,
        "recommendations": recommendations,
        "runtime_diagnostics": diagnostics,
        "diagnostics_totals": dict(flat_runtime_totals),
    }
    report.update({str(key): value for key, value in flat_runtime_totals.items()})
    return report


def compare_reports(
    baseline_report: Mapping[str, Any],
    current_report: Mapping[str, Any],
    tolerance: float = 0.0,
) -> Dict[str, Any]:
    """Compare two quality reports and summarize regressions or improvements."""
    baseline_quality = _report_overall_quality(baseline_report)
    current_quality = _report_overall_quality(current_report)
    overall_quality_delta = current_quality - baseline_quality
    percent_change = 0.0
    if baseline_quality:
        percent_change = (overall_quality_delta / baseline_quality) * 100.0

    section_deltas: Dict[str, float] = {}
    regressed_sections: list[str] = []
    improved_sections: list[str] = []
    score_fields = {
        "structural": ("structural_metrics", "structural_health_score"),
        "semantic": ("semantic_metrics", "semantic_compliance_score"),
        "temporal": ("temporal_metrics", "temporal_consistency_score"),
    }
    for section, (container, score_key) in score_fields.items():
        baseline_section = baseline_report.get(container, {}) if isinstance(baseline_report, Mapping) else {}
        current_section = current_report.get(container, {}) if isinstance(current_report, Mapping) else {}
        delta = _safe_float(current_section.get(score_key)) - _safe_float(baseline_section.get(score_key))
        section_deltas[section] = delta
        if _is_regression_delta(delta, tolerance):
            regressed_sections.append(section)
        elif _is_improvement_delta(delta, tolerance):
            improved_sections.append(section)

    baseline_phase_scores = _report_quality_scores(baseline_report)
    current_phase_scores = _report_quality_scores(current_report)
    phase_names = sorted(set(baseline_phase_scores) | set(current_phase_scores))
    phase_deltas = {
        phase: current_phase_scores.get(phase, 0.0) - baseline_phase_scores.get(phase, 0.0)
        for phase in phase_names
    }

    baseline_temporal_metrics = baseline_report.get("temporal_metrics", {}) if isinstance(baseline_report, Mapping) else {}
    current_temporal_metrics = current_report.get("temporal_metrics", {}) if isinstance(current_report, Mapping) else {}
    temporal_delta_fields = (
        "tlink_conflict_count",
        "tlink_anchor_inconsistent_count",
        "tlink_anchor_self_link_count",
        "tlink_anchor_endpoint_violation_count",
        "tlink_anchor_filter_suppressed_count",
        "tlink_missing_anchor_metadata_count",
        "tlink_reciprocal_cycle_count",
        "isolated_temporal_anchor_count",
        "documents_with_temporal_connectivity_gaps_count",
        "documents_without_temporal_tlinks_count",
        "temporal_issue_count",
    )
    temporal_delta_details = {
        field: _safe_float(current_temporal_metrics.get(field)) - _safe_float(baseline_temporal_metrics.get(field))
        for field in temporal_delta_fields
        if field in baseline_temporal_metrics or field in current_temporal_metrics
    }

    baseline_run_metadata = _copy_mapping(baseline_report.get("run_metadata") if isinstance(baseline_report, Mapping) else {})
    current_run_metadata = _copy_mapping(current_report.get("run_metadata") if isinstance(current_report, Mapping) else {})
    baseline_capture_metadata = _copy_mapping(
        baseline_report.get("capture_metadata") if isinstance(baseline_report, Mapping) else {}
    )
    current_capture_metadata = _copy_mapping(
        current_report.get("capture_metadata") if isinstance(current_report, Mapping) else {}
    )

    is_regression = _is_regression_delta(overall_quality_delta, tolerance) or bool(regressed_sections)
    return {
        "baseline_quality": baseline_quality,
        "current_quality": current_quality,
        "overall_quality_delta": overall_quality_delta,
        "percent_change": percent_change,
        "section_deltas": section_deltas,
        "phase_deltas": phase_deltas,
        "temporal_delta_details": temporal_delta_details,
        "regressed_sections": regressed_sections,
        "improved_sections": improved_sections,
        "baseline_run_metadata": baseline_run_metadata,
        "current_run_metadata": current_run_metadata,
        "baseline_capture_metadata": baseline_capture_metadata,
        "current_capture_metadata": current_capture_metadata,
        "is_regression": is_regression,
        "tolerance": abs(tolerance),
    }


def identify_regression(
    baseline_report: Mapping[str, Any],
    current_report: Mapping[str, Any],
    tolerance: float = 0.0,
) -> tuple[bool, list[str]]:
    """Return a boolean regression flag plus human-readable reasons."""
    comparison = compare_reports(
        baseline_report=baseline_report,
        current_report=current_report,
        tolerance=tolerance,
    )
    reasons: list[str] = []
    if _is_regression_delta(comparison["overall_quality_delta"], tolerance):
        reasons.append(
            "Overall quality regressed by "
            f"{abs(comparison['overall_quality_delta']):.4f} "
            f"({abs(comparison['percent_change']):.1f}%)."
        )
    for section in comparison["regressed_sections"]:
        reasons.append(
            f"{section.title()} quality regressed by {abs(comparison['section_deltas'][section]):.4f}."
        )
    for phase, delta in sorted(comparison["phase_deltas"].items()):
        if _is_regression_delta(delta, tolerance):
            reasons.append(f"Phase '{phase}' regressed by {abs(delta):.4f}.")
    return comparison["is_regression"], reasons


__all__ = [
    "compare_reports",
    "compute_semantic_metrics",
    "compute_structural_metrics",
    "compute_temporal_metrics",
    "generate_quality_report",
    "identify_regression",
    "load_quality_report",
    "overall_quality_from_report",
    "runtime_total_from_report",
]