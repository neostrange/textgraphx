"""Integration of unified metrics and validity headers with evaluation harness.

Provides adapters and utilities for running phases and producing standardized
evaluation reports with full validity certification.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

from textgraphx.evaluation.determinism import compare_metric_results
from textgraphx.evaluation.report_validity import (
    RunMetadata,
    compute_config_hash,
    compute_dataset_hash,
)
from textgraphx.evaluation.unified_metrics import UnifiedMetricReport, create_unified_report


class StandardizedEvaluationRunner:
    """Runnable that produces standardized evaluation reports with validity headers."""

    def __init__(
        self,
        dataset_paths: list[Path],
        config_dict: Dict[str, Any],
        seed: int = 42,
        strict_gate_enabled: bool = True,
        fusion_enabled: bool = False,
        cleanup_mode: str = "auto",
    ):
        """Initialize with run parameters.

        Args:
            dataset_paths: List of gold/dataset files
            config_dict: Runtime config dict (for hashing)
            seed: Random seed for reproducibility
            strict_gate_enabled: Whether strict transition gate is active
            fusion_enabled: Whether cross-document fusion is enabled
            cleanup_mode: Cleanup strategy ("full" | "auto" | "none")
        """
        self.dataset_paths = dataset_paths
        self.config_dict = config_dict
        self.seed = seed
        self.strict_gate_enabled = strict_gate_enabled
        self.fusion_enabled = fusion_enabled
        self.cleanup_mode = cleanup_mode

        # Compute hashes
        self.dataset_hash = compute_dataset_hash(dataset_paths)
        self.config_hash = compute_config_hash(config_dict)

    def create_run_metadata(self, start_time: datetime.datetime, duration_seconds: float) -> RunMetadata:
        """Create RunMetadata for this evaluation run."""
        return RunMetadata(
            dataset_hash=self.dataset_hash,
            config_hash=self.config_hash,
            seed=self.seed,
            strict_gate_enabled=self.strict_gate_enabled,
            fusion_enabled=self.fusion_enabled,
            cleanup_mode=self.cleanup_mode,
            timestamp=start_time.isoformat() + "Z",
            duration_seconds=duration_seconds,
        )

    def create_report(
        self,
        metric_type: str,
        metrics: Dict[str, Any],
        run_metadata: RunMetadata,
        determinism_pass: Optional[bool] = None,
        feature_activation_evidence: Optional[Dict[str, Any]] = None,
        inconclusive_reasons: Optional[list[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UnifiedMetricReport:
        """Create a standardized report."""
        return create_unified_report(
            metric_type=metric_type,
            metrics=metrics,
            run_metadata=run_metadata,
            determinism_pass=determinism_pass,
            feature_activation_evidence=feature_activation_evidence,
            inconclusive_reasons=inconclusive_reasons,
            evidence=evidence,
            metadata=metadata,
        )


def compare_runs_for_determinism(
    report1: UnifiedMetricReport,
    report2: UnifiedMetricReport,
    tolerance: float = 0.0,
) -> tuple[bool, list[str]]:
    """Compare two reports for determinism consistency.

    Args:
        report1: First evaluation report
        report2: Second evaluation report (should have identical run_metadata except timestamp)
        tolerance: Fractional tolerance for numeric diffs

    Returns:
        (is_deterministic, violation_messages)
    """
    # Check if run metadata matches (except timestamp)
    meta1 = report1.validity_header.run_metadata
    meta2 = report2.validity_header.run_metadata

    messages = []
    if meta1.dataset_hash != meta2.dataset_hash:
        messages.append(f"dataset_hash mismatch: {meta1.dataset_hash} vs {meta2.dataset_hash}")
    if meta1.config_hash != meta2.config_hash:
        messages.append(f"config_hash mismatch: {meta1.config_hash} vs {meta2.config_hash}")
    if meta1.seed != meta2.seed:
        messages.append(f"seed mismatch: {meta1.seed} vs {meta2.seed}")
    if meta1.strict_gate_enabled != meta2.strict_gate_enabled:
        messages.append(f"strict_gate_enabled mismatch: {meta1.strict_gate_enabled} vs {meta2.strict_gate_enabled}")
    if meta1.fusion_enabled != meta2.fusion_enabled:
        messages.append(f"fusion_enabled mismatch: {meta1.fusion_enabled} vs {meta2.fusion_enabled}")
    if meta1.cleanup_mode != meta2.cleanup_mode:
        messages.append(f"cleanup_mode mismatch: {meta1.cleanup_mode} vs {meta2.cleanup_mode}")

    if messages:
        return False, ["Run metadata mismatch: " + "; ".join(messages)]

    # Compare metrics
    det_report = compare_metric_results(report1.metrics, report2.metrics, tolerance)
    if not det_report.conclusive:
        messages = [str(v) for v in det_report.violations]
        return False, messages

    return True, []


def load_evaluation_report(path: Path) -> UnifiedMetricReport:
    """Load a previously saved standardized evaluation report."""
    with open(path) as f:
        data = json.load(f)

    from textgraphx.evaluation.report_validity import ValidityHeader

    validity_header = ValidityHeader.from_dict(data["validity_header"])
    return UnifiedMetricReport(
        metric_type=data["metric_type"],
        validity_header=validity_header,
        metrics=data.get("metrics", {}),
        evidence=data.get("evidence", {}),
        metadata=data.get("metadata", {}),
    )
