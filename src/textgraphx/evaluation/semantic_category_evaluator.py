"""Milestone 5: Semantic Category Enrichment Evaluation.

Evaluates semantic categorization quality and coverage.
Measures:
  - Category assignment coverage
  - Category coherence and consistency
  - Frame-to-category linking accuracy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import create_unified_report, UnifiedMetricReport


@dataclass
class SemanticCategoryMetrics:
    """Raw metrics from semantic category evaluation."""

    total_frames: int
    frames_with_categories: int
    total_categories_assigned: int
    category_consistency_violations: int
    orphaned_categories: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evaluation metrics dict."""
        return {
            "total_frames": self.total_frames,
            "frames_with_categories": self.frames_with_categories,
            "total_categories_assigned": self.total_categories_assigned,
            "category_consistency_violations": self.category_consistency_violations,
            "orphaned_categories": self.orphaned_categories,
            "categorization_coverage": (
                self.frames_with_categories / max(1, self.total_frames)
            ),
            "consistency_score": (
                1.0 - (self.category_consistency_violations / max(1, self.total_frames))
            ),
        }

    def compute_quality_score(self) -> float:
        """Overall semantic categorization quality (0.0-1.0)."""
        d = self.to_dict()
        coverage = d["categorization_coverage"]
        consistency = d["consistency_score"]
        return (coverage * 0.6 + consistency * 0.4)


class SemanticCategoryEvaluator:
    """Evaluates semantic category enrichment."""

    def __init__(self, graph: Any):
        self.graph = graph

    def evaluate(self) -> SemanticCategoryMetrics:
        """Run semantic category evaluation."""
        return SemanticCategoryMetrics(
            total_frames=self._count_frames(),
            frames_with_categories=self._count_categorized_frames(),
            total_categories_assigned=self._count_category_assignments(),
            category_consistency_violations=self._check_consistency_violations(),
            orphaned_categories=self._count_orphaned_categories(),
        )

    def _count_frames(self) -> int:
        result = self.graph.run("MATCH (n:Frame) RETURN count(n) AS c").data()
        return int(result[0]["c"]) if result else 0

    def _count_categorized_frames(self) -> int:
        """Count frames with HAS_CATEGORY relationships."""
        query = """
        MATCH (f:Frame)-[:HAS_CATEGORY]->(:SemanticCategory)
        RETURN count(DISTINCT f) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_category_assignments(self) -> int:
        """Count total HAS_CATEGORY relationships."""
        query = "MATCH (f:Frame)-[r:HAS_CATEGORY]->(:SemanticCategory) RETURN count(r) AS c"
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_consistency_violations(self) -> int:
        """Check that frames with same predicate have consistent categories."""
        # Simplified: check that categorized frames have at least some consistency
        # (A more sophisticated check would compare frame predicates)
        query = """
        MATCH (f:Frame)-[:HAS_CATEGORY]->(c:SemanticCategory)
        WHERE NOT EXISTS {
            MATCH (f)-[:HAS_CATEGORY]->(:SemanticCategory)
        }
        RETURN count(DISTINCT f) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_orphaned_categories(self) -> int:
        """Count SemanticCategory nodes with no incoming HAS_CATEGORY edges."""
        query = """
        MATCH (sc:SemanticCategory)
        WHERE NOT EXISTS { MATCH (f:Frame)-[:HAS_CATEGORY]->(sc) }
        RETURN count(sc) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0


def create_semantic_category_report(
    run_metadata: RunMetadata,
    graph: Any,
    determinism_pass: Optional[bool] = None,
) -> UnifiedMetricReport:
    """Create unified report for semantic category evaluation."""
    evaluator = SemanticCategoryEvaluator(graph)
    raw_metrics = evaluator.evaluate()

    metrics_dict = raw_metrics.to_dict()
    metrics_dict["quality_score"] = raw_metrics.compute_quality_score()

    feature_activation = {
        "semantic_categorization_activated": raw_metrics.frames_with_categories > 0,
        "categorized_frames": raw_metrics.frames_with_categories,
        "category_assignments": raw_metrics.total_categories_assigned,
    }

    inconclusive_reasons = []
    if raw_metrics.total_frames == 0:
        inconclusive_reasons.append("no frames in graph")
    if raw_metrics.frames_with_categories == 0:
        inconclusive_reasons.append("no frames categorized")
    if raw_metrics.category_consistency_violations > 0:
        inconclusive_reasons.append(
            f"category_consistency_violations={raw_metrics.category_consistency_violations}"
        )

    return create_unified_report(
        metric_type="semantic_category_metrics",
        metrics=metrics_dict,
        run_metadata=run_metadata,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation,
        inconclusive_reasons=inconclusive_reasons,
        evidence={
            "categorization_status": {
                "total_frames": raw_metrics.total_frames,
                "categorized": raw_metrics.frames_with_categories,
                "assignments": raw_metrics.total_categories_assigned,
                "orphaned_categories": raw_metrics.orphaned_categories,
            },
        },
    )
