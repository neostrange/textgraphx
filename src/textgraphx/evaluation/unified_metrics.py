"""Unified evaluation metrics schema with validity headers.

All evaluation artifacts (mentions, edges, metrics) use this standardized
schema to include validity metadata, feature activation evidence, and
determinism checking status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from textgraphx.evaluation.report_validity import (
    RunMetadata,
    ValidityHeader,
    render_validity_header_json,
)


@dataclass
class UnifiedMetricReport:
    """Standard container for all evaluation metrics with validity certification."""

    metric_type: str  # "edge_metrics", "mention_metrics", "phase_metrics", etc.
    validity_header: ValidityHeader
    metrics: Dict[str, Any]  # The actual computed metrics
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting data (e.g., edge types)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/YAML output."""
        result = {
            "metric_type": self.metric_type,
            "validity_header": self.validity_header.to_dict(),
            "metrics": self.metrics,
        }
        if self.evidence:
            result["evidence"] = self.evidence
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_json_file(self, path: Path) -> None:
        """Write report to JSON file with indentation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def to_markdown_with_header(self) -> str:
        """Render as markdown with YAML frontmatter validity header."""
        from textgraphx.evaluation.report_validity import render_validity_header_yaml

        header_yaml = render_validity_header_yaml(self.validity_header)
        body = self._render_metrics_markdown()
        return f"{header_yaml}\n\n{body}"

    def _render_metrics_markdown(self) -> str:
        """Render metrics section as markdown."""
        lines = [f"# {self.metric_type} Report"]
        lines.append("")

        # Metrics table
        if self.metrics:
            lines.append("## Metrics")
            lines.append("")
            for k, v in sorted(self.metrics.items()):
                if isinstance(v, float):
                    lines.append(f"- **{k}**: {v:.4f}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append("")

        # Evidence
        if self.evidence:
            lines.append("## Evidence")
            lines.append("")
            for k, v in sorted(self.evidence.items()):
                if isinstance(v, dict):
                    lines.append(f"### {k}")
                    for ek, ev in sorted(v.items()):
                        lines.append(f"  - {ek}: {ev}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append("")

        # Metadata
        if self.metadata:
            lines.append("## Metadata")
            lines.append("")
            for k, v in sorted(self.metadata.items()):
                lines.append(f"- **{k}**: {v}")

        return "\n".join(lines)


def create_unified_report(
    metric_type: str,
    metrics: Dict[str, Any],
    run_metadata: RunMetadata,
    determinism_pass: Optional[bool] = None,
    feature_activation_evidence: Optional[Dict[str, Any]] = None,
    inconclusive_reasons: Optional[List[str]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedMetricReport:
    """Factory function to create a unified report with all required fields.

    Args:
        metric_type: Type of metric (e.g., "edge_metrics", "mention_metrics")
        metrics: Computed metrics dict
        run_metadata: RunMetadata describing the run parameters
        determinism_pass: True if determinism check passed, None if not checked
        feature_activation_evidence: Dict of feature activation counts/stats
        inconclusive_reasons: List of reasons why this result is inconclusive
        evidence: Supporting evidence/breakdown data
        metadata: Additional context

    Returns:
        UnifiedMetricReport ready for export
    """
    header = ValidityHeader(
        run_metadata=run_metadata,
        determinism_checked=determinism_pass is not None,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation_evidence or {},
        inconclusive_reasons=inconclusive_reasons or [],
    )

    return UnifiedMetricReport(
        metric_type=metric_type,
        validity_header=header,
        metrics=metrics,
        evidence=evidence or {},
        metadata=metadata or {},
    )
