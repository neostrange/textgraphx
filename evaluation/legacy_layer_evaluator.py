"""Milestone 6: Legacy Layer Backward Compatibility Evaluation.

Evaluates that legacy patterns and data remain accessible after semantic upgrades.
Measures:
  - Legacy node availability
  - Legacy relationship preservation
  - Migration completion and consistency
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import create_unified_report, UnifiedMetricReport


@dataclass
class LegacyLayerMetrics:
    """Raw metrics from legacy layer evaluation."""

    legacy_nodes_total: int
    legacy_nodes_active: int
    legacy_relationships_total: int
    legacy_relationships_active: int
    migration_dual_nodes: int  # Nodes with both old and new labels
    migration_dual_rels: int  # Relationships with both old and new paths
    legacy_orphans: int  # Legacy data without new counterparts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evaluation metrics dict."""
        return {
            "legacy_nodes_total": self.legacy_nodes_total,
            "legacy_nodes_active": self.legacy_nodes_active,
            "legacy_relationships_total": self.legacy_relationships_total,
            "legacy_relationships_active": self.legacy_relationships_active,
            "migration_dual_nodes": self.migration_dual_nodes,
            "migration_dual_rels": self.migration_dual_rels,
            "legacy_orphans": self.legacy_orphans,
            "legacy_preservation_rate": (
                self.legacy_nodes_active / max(1, self.legacy_nodes_total)
            ),
            "legacy_relationship_preservation_rate": (
                self.legacy_relationships_active / max(1, self.legacy_relationships_total)
            ),
        }

    def compute_quality_score(self) -> float:
        """Overall legacy compatibility quality (0.0-1.0)."""
        d = self.to_dict()
        if self.legacy_orphans > 0:
            # Orphaned legacy data means incomplete migration
            orphan_rate = self.legacy_orphans / max(1, self.legacy_nodes_total)
            return max(0.0, 1.0 - orphan_rate)
        
        node_rate = d["legacy_preservation_rate"]
        rel_rate = d["legacy_relationship_preservation_rate"]
        return (node_rate * 0.5 + rel_rate * 0.5)


class LegacyLayerEvaluator:
    """Evaluates legacy data preservation and migration."""

    def __init__(self, graph: Any):
        self.graph = graph

    def evaluate(self) -> LegacyLayerMetrics:
        """Run legacy layer evaluation."""
        return LegacyLayerMetrics(
            legacy_nodes_total=self._count_legacy_nodes(),
            legacy_nodes_active=self._count_active_legacy_nodes(),
            legacy_relationships_total=self._count_legacy_relationships(),
            legacy_relationships_active=self._count_active_legacy_relationships(),
            migration_dual_nodes=self._count_dual_label_nodes(),
            migration_dual_rels=self._count_dual_path_relationships(),
            legacy_orphans=self._count_orphaned_legacy_nodes(),
        )

    def _count_legacy_nodes(self) -> int:
        """Count nodes with legacy labels (NamedEntity, TEvent, Frame)."""
        query = """
        MATCH (n:NamedEntity|TEvent|Frame)
        RETURN count(n) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_active_legacy_nodes(self) -> int:
        """Count legacy nodes that are actually used (have properties/relationships)."""
        query = """
        MATCH (n:NamedEntity|TEvent|Frame)
        WHERE n.doc_id IS NOT NULL
        RETURN count(n) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_legacy_relationships(self) -> int:
        """Count relationships using legacy types (PARTICIPANT, DESCRIBES, etc)."""
        query = """
        MATCH ()-[r:PARTICIPANT|DESCRIBES|DESCRIBES_EVENT|EVENT_PARTICIPANT]-()
        RETURN count(r) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_active_legacy_relationships(self) -> int:
        """Count legacy relationships that connect to populated nodes."""
        query = """
        MATCH (a:NamedEntity|TEvent|Frame)-[r:PARTICIPANT|DESCRIBES|DESCRIBES_EVENT|EVENT_PARTICIPANT]-(b:NamedEntity|TEvent|Frame)
        RETURN count(r) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_dual_label_nodes(self) -> int:
        """Count nodes with both old and new labels (NamedEntity + EntityMention, etc)."""
        query = """
        MATCH (n:NamedEntity:EntityMention)
        RETURN count(n) AS em_count
        """
        result1 = self.graph.run(query).data()
        em_count = int(result1[0]["em_count"]) if result1 else 0

        query = """
        MATCH (n:TEvent:EventMention)
        RETURN count(n) AS tm_count
        """
        result2 = self.graph.run(query).data()
        tm_count = int(result2[0]["tm_count"]) if result2 else 0

        return em_count + tm_count

    def _count_dual_path_relationships(self) -> int:
        """Count relationships available via both old and new paths."""
        # Old: Entity->TEvent, New: Entity->EventMention->TEvent
        query = """
        MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(te:TEvent)
        OPTIONAL MATCH (e)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(em:EventMention)-[:REFERS_TO]->(te)
        RETURN count(CASE WHEN em IS NOT NULL THEN 1 END) AS dual_count
        """
        result = self.graph.run(query).data()
        return int(result[0]["dual_count"]) if result else 0

    def _count_orphaned_legacy_nodes(self) -> int:
        """Count legacy nodes without corresponding new layer nodes."""
        query = """
        MATCH (ne:NamedEntity)
        WHERE NOT EXISTS { MATCH (ne)-[:REFERS_TO]->(e:Entity) }
        AND NOT EXISTS { MATCH (ne:EntityMention) }
        RETURN count(ne) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0


def create_legacy_layer_report(
    run_metadata: RunMetadata,
    graph: Any,
    determinism_pass: Optional[bool] = None,
) -> UnifiedMetricReport:
    """Create unified report for legacy layer evaluation."""
    evaluator = LegacyLayerEvaluator(graph)
    raw_metrics = evaluator.evaluate()

    metrics_dict = raw_metrics.to_dict()
    metrics_dict["quality_score"] = raw_metrics.compute_quality_score()

    feature_activation = {
        "legacy_data_preserved": raw_metrics.legacy_nodes_active > 0,
        "legacy_nodes": raw_metrics.legacy_nodes_active,
        "dual_labeled_nodes": raw_metrics.migration_dual_nodes,
    }

    inconclusive_reasons = []
    if raw_metrics.legacy_nodes_total == 0:
        inconclusive_reasons.append("no legacy nodes to evaluate")
    if raw_metrics.legacy_orphans > 0:
        inconclusive_reasons.append(
            f"orphaned_legacy_nodes={raw_metrics.legacy_orphans}"
        )

    return create_unified_report(
        metric_type="legacy_layer_metrics",
        metrics=metrics_dict,
        run_metadata=run_metadata,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation,
        inconclusive_reasons=inconclusive_reasons,
        evidence={
            "legacy_population": {
                "nodes_total": raw_metrics.legacy_nodes_total,
                "nodes_active": raw_metrics.legacy_nodes_active,
                "relationships_total": raw_metrics.legacy_relationships_total,
                "relationships_active": raw_metrics.legacy_relationships_active,
            },
            "migration_status": {
                "dual_labeled_nodes": raw_metrics.migration_dual_nodes,
                "dual_path_relationships": raw_metrics.migration_dual_rels,
                "orphaned_nodes": raw_metrics.legacy_orphans,
            },
        },
    )
