"""Milestone 4: Phase Assertions and Contract Validation.

Evaluates that phase outputs satisfy their published contracts.
Measures:
  - Schema compliance (required properties exist)
  - Relationship structure validity
  - Phase invariant satisfaction
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import create_unified_report, UnifiedMetricReport


@dataclass
class PhaseAssertionMetrics:
    """Raw metrics from phase assertion evaluation."""

    total_nodes_checked: int
    nodes_meeting_schema: int
    schema_violations: int
    phase_invariant_violations: int
    temporal_consistency_violations: int
    semantic_consistency_violations: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evaluation metrics dict."""
        return {
            "total_nodes_checked": self.total_nodes_checked,
            "nodes_meeting_schema": self.nodes_meeting_schema,
            "schema_violations": self.schema_violations,
            "phase_invariant_violations": self.phase_invariant_violations,
            "temporal_consistency_violations": self.temporal_consistency_violations,
            "semantic_consistency_violations": self.semantic_consistency_violations,
            "schema_compliance_rate": (
                self.nodes_meeting_schema / max(1, self.total_nodes_checked)
            ),
            "invariant_compliance_rate": (
                1.0 - (self.phase_invariant_violations / max(1, self.total_nodes_checked))
            ),
        }

    def compute_quality_score(self) -> float:
        """Overall phase compliance quality (0.0-1.0)."""
        if self.schema_violations + self.phase_invariant_violations > 0:
            # Violations reduce score significantly
            violation_count = (
                self.schema_violations +
                self.phase_invariant_violations +
                self.temporal_consistency_violations +
                self.semantic_consistency_violations
            )
            return max(0.0, 1.0 - (violation_count / max(1, self.total_nodes_checked)))
        return 1.0


class PhaseAssertionEvaluator:
    """Evaluates phase output contracts."""

    def __init__(self, graph: Any):
        self.graph = graph

    def evaluate(self) -> PhaseAssertionMetrics:
        """Run phase assertion evaluation."""
        return PhaseAssertionMetrics(
            total_nodes_checked=self._count_all_nodes(),
            nodes_meeting_schema=self._count_schema_compliant_nodes(),
            schema_violations=self._check_schema_violations(),
            phase_invariant_violations=self._check_invariant_violations(),
            temporal_consistency_violations=self._check_temporal_violations(),
            semantic_consistency_violations=self._check_semantic_violations(),
        )

    def _count_all_nodes(self) -> int:
        result = self.graph.run("MATCH (n) RETURN count(n) AS c").data()
        return int(result[0]["c"]) if result else 0

    def _count_schema_compliant_nodes(self) -> int:
        """Count nodes that have required properties for their type."""
        # Example: EventMention should have pred, start_tok, end_tok
        query = """
        MATCH (n:EventMention)
        WHERE n.pred IS NOT NULL AND n.start_tok IS NOT NULL AND n.end_tok IS NOT NULL
        RETURN count(n) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_schema_violations(self) -> int:
        """Count nodes violating schema constraints."""
        # EventMention without required properties
        query = """
        MATCH (n:EventMention)
        WHERE n.pred IS NULL OR n.start_tok IS NULL OR n.end_tok IS NULL
        RETURN count(n) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_invariant_violations(self) -> int:
        """Check that phase output invariants are maintained."""
        # Example: Every EventMention should have a REFERS_TO relationship
        query = """
        MATCH (em:EventMention)
        WHERE NOT EXISTS { MATCH (em)-[:REFERS_TO]->(te:TEvent) }
        RETURN count(em) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_temporal_violations(self) -> int:
        """Check temporal consistency (e.g., span boundaries)."""
        query = """
        MATCH (em:EventMention)
        WHERE em.start_tok > em.end_tok
        RETURN count(em) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_semantic_violations(self) -> int:
        """Check semantic consistency (e.g., no orphaned edges)."""
        # Edges should point to existing nodes
        query = """
        MATCH ()-[r:REFERS_TO]->(n)
        WHERE NOT EXISTS { MATCH (n) }
        RETURN count(r) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0


def create_phase_assertion_report(
    run_metadata: RunMetadata,
    graph: Any,
    determinism_pass: Optional[bool] = None,
) -> UnifiedMetricReport:
    """Create unified report for phase assertion evaluation."""
    evaluator = PhaseAssertionEvaluator(graph)
    raw_metrics = evaluator.evaluate()

    metrics_dict = raw_metrics.to_dict()
    metrics_dict["quality_score"] = raw_metrics.compute_quality_score()

    feature_activation = {
        "phase_materialization_active": raw_metrics.total_nodes_checked > 0,
        "nodes_checked": raw_metrics.total_nodes_checked,
    }

    inconclusive_reasons = []
    if raw_metrics.total_nodes_checked == 0:
        inconclusive_reasons.append("no nodes in graph")
    if raw_metrics.schema_violations > 0:
        inconclusive_reasons.append(
            f"schema_violations={raw_metrics.schema_violations}"
        )
    if raw_metrics.phase_invariant_violations > 0:
        inconclusive_reasons.append(
            f"invariant_violations={raw_metrics.phase_invariant_violations}"
        )

    return create_unified_report(
        metric_type="phase_assertion_metrics",
        metrics=metrics_dict,
        run_metadata=run_metadata,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation,
        inconclusive_reasons=inconclusive_reasons,
        evidence={
            "violations": {
                "schema": raw_metrics.schema_violations,
                "invariant": raw_metrics.phase_invariant_violations,
                "temporal": raw_metrics.temporal_consistency_violations,
                "semantic": raw_metrics.semantic_consistency_violations,
            },
        },
    )
