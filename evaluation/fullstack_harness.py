"""Milestone 7: Full-Stack Unified Evaluation Harness.

End-to-end evaluation orchestrator that runs all phase evaluations with unified
validity headers, determinism verification, and comprehensive reporting.

Provides:
  - Single entry point for full pipeline evaluation
  - Determinism verification across all phases
  - Holistic quality scoring
  - CSV and JSON export for comparison
  - Markdown report generation with all validity headers
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from textgraphx.evaluation.determinism import compare_metric_results
from textgraphx.evaluation.edge_semantics_evaluator import create_edge_semantics_report
from textgraphx.evaluation.integration import StandardizedEvaluationRunner
from textgraphx.evaluation.legacy_layer_evaluator import create_legacy_layer_report
from textgraphx.evaluation.mention_layer_evaluator import create_mention_layer_report
from textgraphx.evaluation.phase_assertion_evaluator import create_phase_assertion_report
from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.semantic_category_evaluator import create_semantic_category_report
from textgraphx.evaluation.unified_metrics import UnifiedMetricReport
from textgraphx.diagnostics import get_runtime_metrics


@dataclass
class EvaluationSuite:
    """Container for all phase evaluation reports."""

    run_metadata: RunMetadata
    mention_layer: UnifiedMetricReport
    edge_semantics: UnifiedMetricReport
    phase_assertions: UnifiedMetricReport
    semantic_categories: UnifiedMetricReport
    legacy_layer: UnifiedMetricReport
    elapsed_seconds: float
    runtime_diagnostics: Optional[Dict[str, Any]] = None

    @property
    def all_reports(self) -> List[UnifiedMetricReport]:
        """All reports in evaluation suite."""
        return [
            self.mention_layer,
            self.edge_semantics,
            self.phase_assertions,
            self.semantic_categories,
            self.legacy_layer,
        ]

    def quality_scores(self) -> Dict[str, float]:
        """Quality scores by phase."""
        return {
            "mention_layer": self.mention_layer.metrics.get("quality_score", 0.0),
            "edge_semantics": self.edge_semantics.metrics.get("quality_score", 0.0),
            "phase_assertions": self.phase_assertions.metrics.get("quality_score", 0.0),
            "semantic_categories": self.semantic_categories.metrics.get("quality_score", 0.0),
            "legacy_layer": self.legacy_layer.metrics.get("quality_score", 0.0),
        }

    def overall_quality(self) -> float:
        """Macro-average quality across all phases."""
        scores = self.quality_scores()
        if not scores:
            return 0.0
        return sum(scores.values()) / len(scores)

    def conclusiveness(self) -> tuple[bool, List[str]]:
        """Overall conclusiveness and reasons for inconclusiveness."""
        reasons = []
        for i, report in enumerate(self.all_reports):
            if not report.validity_header.to_dict()["is_conclusive"]:
                reasons.extend([
                    f"{report.metric_type}: {r}"
                    for r in report.validity_header.inconclusive_reasons
                ])
        return len(reasons) == 0, reasons

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON export."""
        return {
            "run_metadata": self.run_metadata.to_dict(),
            "execution_time_seconds": self.elapsed_seconds,
            "quality_scores": self.quality_scores(),
            "overall_quality": self.overall_quality(),
            "conclusiveness": {
                "conclusive": self.conclusiveness()[0],
                "reasons": self.conclusiveness()[1],
            },
            "reports": {
                report.metric_type: report.to_dict()
                for report in self.all_reports
            },
            "runtime_diagnostics": self.runtime_diagnostics or {},
        }


class FullStackEvaluator:
    """Orchestrates full-stack evaluation of all phases."""

    def __init__(
        self,
        graph: Any,
        dataset_paths: List[Path],
        config_dict: Dict[str, Any],
        seed: int = 42,
        strict_gate_enabled: bool = True,
        fusion_enabled: bool = False,
        cleanup_mode: str = "auto",
    ):
        """Initialize evaluator.

        Args:
            graph: Neo4j graph connection
            dataset_paths: List of gold/reference files
            config_dict: Runtime config dict
            seed: Random seed for reproducibility
            strict_gate_enabled: Whether strict transition gate is enabled
            fusion_enabled: Whether cross-document fusion is enabled
            cleanup_mode: Cleanup strategy
        """
        self.graph = graph
        self.runner = StandardizedEvaluationRunner(
            dataset_paths=dataset_paths,
            config_dict=config_dict,
            seed=seed,
            strict_gate_enabled=strict_gate_enabled,
            fusion_enabled=fusion_enabled,
            cleanup_mode=cleanup_mode,
        )

    def evaluate(self, determinism_pass: Optional[bool] = None) -> EvaluationSuite:
        """Run complete evaluation suite.

        Args:
            determinism_pass: Whether determinism check passed (optional)

        Returns:
            EvaluationSuite with all phase reports
        """
        start_time = datetime.now(timezone.utc)
        meta = self.runner.create_run_metadata(start_time, 0.0)

        # Run all phase evaluations
        mention_layer = create_mention_layer_report(
            meta, self.graph, determinism_pass
        )
        edge_semantics = create_edge_semantics_report(
            meta, self.graph, determinism_pass
        )
        phase_assertions = create_phase_assertion_report(
            meta, self.graph, determinism_pass
        )
        semantic_categories = create_semantic_category_report(
            meta, self.graph, determinism_pass
        )
        legacy_layer = create_legacy_layer_report(
            meta, self.graph, determinism_pass
        )
        try:
            runtime_diagnostics = get_runtime_metrics(self.graph)
        except Exception as exc:
            runtime_diagnostics = {
                "error": f"runtime diagnostics unavailable: {exc}",
            }

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        meta.duration_seconds = elapsed

        return EvaluationSuite(
            run_metadata=meta,
            mention_layer=mention_layer,
            edge_semantics=edge_semantics,
            phase_assertions=phase_assertions,
            semantic_categories=semantic_categories,
            legacy_layer=legacy_layer,
            elapsed_seconds=elapsed,
            runtime_diagnostics=runtime_diagnostics,
        )

    def export_json(self, suite: EvaluationSuite, path: Path) -> None:
        """Export evaluation suite to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(suite.to_dict(), f, indent=2, default=str)

    def export_markdown(self, suite: EvaluationSuite, path: Path) -> None:
        """Export evaluation suite as markdown with individual report headers."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            # Main header
            f.write("# Full-Stack Evaluation Report\n\n")
            f.write(f"**Date**: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"**Overall Quality**: {suite.overall_quality():.4f}\n")
            f.write(f"**Conclusive**: {suite.conclusiveness()[0]}\n\n")

            # Quality scores summary
            f.write("## Quality Scores by Phase\n\n")
            for phase, score in suite.quality_scores().items():
                f.write(f"- {phase}: {score:.4f}\n")
            f.write("\n")

            # Runtime diagnostics summary
            f.write("## Runtime Diagnostics\n\n")
            diagnostics = suite.runtime_diagnostics or {}
            totals = diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {}
            if totals:
                for key in sorted(totals.keys()):
                    value = totals[key]
                    if isinstance(value, float):
                        f.write(f"- {key}: {value:.4f}\n")
                    else:
                        f.write(f"- {key}: {value}\n")
            else:
                if isinstance(diagnostics, dict) and diagnostics.get("error"):
                    f.write(f"- error: {diagnostics['error']}\n")
                else:
                    f.write("- no runtime diagnostics available\n")
            f.write("\n")

            # Each report with its validity header
            for report in suite.all_reports:
                f.write(f"## {report.metric_type}\n\n")
                f.write(report.to_markdown_with_header())
                f.write("\n\n")

    def export_csv(self, suite: EvaluationSuite, path: Path) -> None:
        """Export quality scores and key metrics as CSV for easy comparison."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        rows = []
        for report in suite.all_reports:
            row = {
                "metric_type": report.metric_type,
                "overall_quality": suite.overall_quality(),
                "phase_quality": report.metrics.get("quality_score", 0.0),
                "conclusive": len(report.validity_header.inconclusive_reasons) == 0,
                "seed": report.validity_header.run_metadata.seed,
                "fusion_enabled": report.validity_header.run_metadata.fusion_enabled,
            }
            rows.append(row)

        with open(path, "w", newline="") as f:
            if rows:
                fieldnames = list(rows[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)


def compare_evaluation_suites(
    suite1: EvaluationSuite,
    suite2: EvaluationSuite,
    tolerance: float = 0.0,
) -> tuple[bool, List[str]]:
    """Compare two evaluation suites for determinism/consistency.

    Args:
        suite1: First evaluation suite
        suite2: Second evaluation suite
        tolerance: Fractional tolerance for numeric comparisons

    Returns:
        (is_consistent, messages)
    """
    messages = []

    if suite1.run_metadata.dataset_hash != suite2.run_metadata.dataset_hash:
        messages.append("Dataset hash mismatch")
    if suite1.run_metadata.config_hash != suite2.run_metadata.config_hash:
        messages.append("Config hash mismatch")
    if suite1.run_metadata.seed != suite2.run_metadata.seed:
        messages.append("Seed mismatch")

    # Compare each phase report
    for report1, report2 in zip(suite1.all_reports, suite2.all_reports):
        det_report = compare_metric_results(
            report1.metrics, report2.metrics, tolerance
        )
        if not det_report.conclusive:
            messages.append(f"{report1.metric_type}: {det_report.summary}")

    return len(messages) == 0, messages
