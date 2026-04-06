"""Milestone 3: Unified evaluation of Edge Semantics (Phase 4).

Evaluates edge semantic enrichment with validity headers.
Measures:
  - Edge type coverage and distribution
  - Semantic relationship correctness
  - Enrichment completeness
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import create_unified_report, UnifiedMetricReport


@dataclass
class EdgeSemanticsMetrics:
    """Raw metrics from edge semantics evaluation."""

    total_edges: int
    typed_edges: int  # Edges with explicit semantic type
    same_as_edges: int
    co_occurs_edges: int
    participant_edges: int
    instantiates_edges: int
    refers_to_edges: int
    untyped_edges: int
    semantic_coherence_violations: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evaluation metrics dict."""
        return {
            "total_edges": self.total_edges,
            "typed_edges": self.typed_edges,
            "same_as_edges": self.same_as_edges,
            "co_occurs_edges": self.co_occurs_edges,
            "participant_edges": self.participant_edges,
            "instantiates_edges": self.instantiates_edges,
            "refers_to_edges": self.refers_to_edges,
            "untyped_edges": self.untyped_edges,
            "semantic_coherence_violations": self.semantic_coherence_violations,
            "typing_coverage": (
                self.typed_edges / max(1, self.total_edges)
            ),
            "coherence_score": (
                1.0 - (self.semantic_coherence_violations / max(1, self.total_edges))
            ),
        }

    def compute_quality_score(self) -> float:
        """Overall edge semantics quality (0.0-1.0)."""
        d = self.to_dict()
        # Typing and coherence are equally important
        return (d["typing_coverage"] * 0.5 + d["coherence_score"] * 0.5)


class EdgeSemanticsEvaluator:
    """Evaluates edge semantic enrichment."""

    def __init__(self, graph: Any):
        self.graph = graph

    def evaluate(self) -> EdgeSemanticsMetrics:
        """Run edge semantics evaluation."""
        return EdgeSemanticsMetrics(
            total_edges=self._count_all_edges(),
            typed_edges=self._count_typed_edges(),
            same_as_edges=self._count_edge_type("SAME_AS"),
            co_occurs_edges=self._count_edge_type("CO_OCCURS_WITH"),
            participant_edges=self._count_edge_type("PARTICIPANT|EVENT_PARTICIPANT"),
            instantiates_edges=self._count_edge_type("INSTANTIATES"),
            refers_to_edges=self._count_edge_type("REFERS_TO"),
            untyped_edges=self._count_untyped_edges(),
            semantic_coherence_violations=self._check_coherence_violations(),
        )

    def _count_all_edges(self) -> int:
        result = self.graph.run("MATCH ()-[r]->() RETURN count(r) AS c").data()
        return int(result[0]["c"]) if result else 0

    def _count_typed_edges(self) -> int:
        """Edges with explicit relationship type."""
        result = self.graph.run(
            "MATCH ()-[r]->() WHERE r.type IS NOT NULL RETURN count(r) AS c"
        ).data()
        return int(result[0]["c"]) if result else 0

    def _count_edge_type(self, rel_types: str) -> int:
        """Count edges with specific relationship type(s)."""
        query = f"MATCH ()-[r:{rel_types}]->() RETURN count(r) AS c"
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_untyped_edges(self) -> int:
        """Count edges without type property."""
        result = self.graph.run(
            "MATCH ()-[r]->() WHERE r.type IS NULL RETURN count(r) AS c"
        ).data()
        return int(result[0]["c"]) if result else 0

    def _check_coherence_violations(self) -> int:
        """Check for semantic inconsistencies (e.g., SAME_AS between different types)."""
        # SAME_AS should only link nodes of the same semantic type
        query = """
        MATCH (a:EntityMention)-[:SAME_AS]->(b:EntityMention)
        WHERE a.__type__ != b.__type__
        RETURN count(*) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0


def create_edge_semantics_report(
    run_metadata: RunMetadata,
    graph: Any,
    determinism_pass: Optional[bool] = None,
) -> UnifiedMetricReport:
    """Create unified report for edge semantics evaluation."""
    evaluator = EdgeSemanticsEvaluator(graph)
    raw_metrics = evaluator.evaluate()

    metrics_dict = raw_metrics.to_dict()
    metrics_dict["quality_score"] = raw_metrics.compute_quality_score()

    feature_activation = {
        "semantic_typing_activated": raw_metrics.typed_edges > 0,
        "same_as_edges_created": raw_metrics.same_as_edges,
        "co_occurs_edges_created": raw_metrics.co_occurs_edges,
    }

    inconclusive_reasons = []
    if raw_metrics.semantic_coherence_violations > 0:
        inconclusive_reasons.append(
            f"semantic_coherence_violations={raw_metrics.semantic_coherence_violations}"
        )
    if raw_metrics.total_edges == 0:
        inconclusive_reasons.append("no edges in graph")

    return create_unified_report(
        metric_type="edge_semantics_metrics",
        metrics=metrics_dict,
        run_metadata=run_metadata,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation,
        inconclusive_reasons=inconclusive_reasons,
        evidence={
            "edge_distribution": {
                "SAME_AS": raw_metrics.same_as_edges,
                "CO_OCCURS": raw_metrics.co_occurs_edges,
                "PARTICIPANT": raw_metrics.participant_edges,
                "INSTANTIATES": raw_metrics.instantiates_edges,
                "REFERS_TO": raw_metrics.refers_to_edges,
            },
        },
    )
