"""Milestone 2: Unified evaluation of Mention Layer (Phase 1).

Integrates mention layer validation with unified metrics schema and validity headers.
Measures:
  - EntityMention introduction correctness
  - EventMention introduction correctness
  - REFERS_TO linking accuracy
  - Backward compatibility preservation
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import create_unified_report, UnifiedMetricReport


@dataclass
class MentionLayerMetrics:
    """Raw metrics from mention layer validation."""

    entity_mentions_created: int
    entity_mentions_with_refers_to: int
    event_mentions_created: int
    event_mentions_with_refers_to: int
    frame_instantiates_event_mention: int
    entity_participant_links: int
    event_participant_links: int
    backward_compatibility_violations: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evaluation metrics dict."""
        return {
            "entity_mentions_created": self.entity_mentions_created,
            "entity_mentions_with_refers_to": self.entity_mentions_with_refers_to,
            "event_mentions_created": self.event_mentions_created,
            "event_mentions_with_refers_to": self.event_mentions_with_refers_to,
            "frame_instantiates_event_mention": self.frame_instantiates_event_mention,
            "entity_participant_links": self.entity_participant_links,
            "event_participant_links": self.event_participant_links,
            "backward_compatibility_violations": self.backward_compatibility_violations,
            # Derived metrics
            "entity_mention_refers_to_rate": (
                self.entity_mentions_with_refers_to / max(1, self.entity_mentions_created)
            ),
            "event_mention_refers_to_rate": (
                self.event_mentions_with_refers_to / max(1, self.event_mentions_created)
            ),
            "frame_instantiation_coverage": (
                self.frame_instantiates_event_mention / max(1, self.event_mentions_created)
            ),
        }

    def compute_quality_score(self) -> float:
        """Compute overall mention layer quality (0.0-1.0)."""
        if self.backward_compatibility_violations > 0:
            return 0.0  # Backward compat is non-optional

        d = self.to_dict()
        entity_rate = d["entity_mention_refers_to_rate"]
        event_rate = d["event_mention_refers_to_rate"]
        frame_coverage = d["frame_instantiation_coverage"]

        # Weighted average
        return (entity_rate * 0.3 + event_rate * 0.3 + frame_coverage * 0.4)


class MentionLayerEvaluator:
    """Evaluator for mention layer conformance and quality."""

    def __init__(self, graph: Any):
        """Initialize with Neo4j graph connection."""
        self.graph = graph

    def evaluate(self) -> MentionLayerMetrics:
        """Run full mention layer evaluation and return raw metrics."""
        entity_mentions_created = self._count_entity_mentions()
        entity_mentions_with_refers_to = self._count_entity_mentions_with_refers_to()
        event_mentions_created = self._count_event_mentions()
        event_mentions_with_refers_to = self._count_event_mentions_with_refers_to()
        frame_instantiates = self._count_frame_instantiates_event_mention()
        entity_participants = self._count_entity_participant_links()
        event_participants = self._count_event_participant_links()
        compat_violations = self._check_backward_compatibility_violations()

        return MentionLayerMetrics(
            entity_mentions_created=entity_mentions_created,
            entity_mentions_with_refers_to=entity_mentions_with_refers_to,
            event_mentions_created=event_mentions_created,
            event_mentions_with_refers_to=event_mentions_with_refers_to,
            frame_instantiates_event_mention=frame_instantiates,
            entity_participant_links=entity_participants,
            event_participant_links=event_participants,
            backward_compatibility_violations=compat_violations,
        )

    def _count_entity_mentions(self) -> int:
        """Count total EntityMention nodes."""
        result = self.graph.run("MATCH (n:EntityMention) RETURN count(n) AS c").data()
        return int(result[0]["c"]) if result else 0

    def _count_entity_mentions_with_refers_to(self) -> int:
        """Count EntityMention nodes with REFERS_TO relationships."""
        query = "MATCH (em:EntityMention)-[:REFERS_TO]->(e:Entity) RETURN count(*) AS c"
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_event_mentions(self) -> int:
        """Count total EventMention nodes."""
        result = self.graph.run("MATCH (n:EventMention) RETURN count(n) AS c").data()
        return int(result[0]["c"]) if result else 0

    def _count_event_mentions_with_refers_to(self) -> int:
        """Count EventMention nodes with REFERS_TO relationships."""
        query = "MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent) RETURN count(*) AS c"
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_frame_instantiates_event_mention(self) -> int:
        """Count Frame -[:INSTANTIATES]-> EventMention relationships."""
        query = "MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention) RETURN count(*) AS c"
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_entity_participant_links(self) -> int:
        """Count Entity (direct or via EventMention) participant relationships."""
        query = """
        MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(em:EventMention)
        RETURN count(*) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _count_event_participant_links(self) -> int:
        """Count existing TEvent participant relationships (for backward compat check)."""
        query = """
        MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(te:TEvent)
        RETURN count(*) AS c
        """
        result = self.graph.run(query).data()
        return int(result[0]["c"]) if result else 0

    def _check_backward_compatibility_violations(self) -> int:
        """Check if any old patterns were broken (should be 0)."""
        # Old: Entity->TEvent relationships must still exist
        query = """
        MATCH (te:TEvent)
        WHERE NOT EXISTS {
            MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(te)
        }
        RETURN count(*) AS c
        """
        result = self.graph.run(query).data()
        violations = int(result[0]["c"]) if result else 0
        return violations


def create_mention_layer_report(
    run_metadata: RunMetadata,
    graph: Any,
    determinism_pass: Optional[bool] = None,
) -> UnifiedMetricReport:
    """Create a unified evaluation report for the mention layer.

    Args:
        run_metadata: RunMetadata from evaluation runner
        graph: Neo4j graph connection
        determinism_pass: Whether determinism check passed

    Returns:
        UnifiedMetricReport with mention layer metrics and validity header
    """
    evaluator = MentionLayerEvaluator(graph)
    raw_metrics = evaluator.evaluate()

    # Convert to report format
    metrics_dict = raw_metrics.to_dict()
    metrics_dict["quality_score"] = raw_metrics.compute_quality_score()

    # Feature activation: mention layer is enabled if entities/events created
    feature_activation = {
        "entity_mentions_activated": raw_metrics.entity_mentions_created > 0,
        "event_mentions_activated": raw_metrics.event_mentions_created > 0,
        "entity_mention_count": raw_metrics.entity_mentions_created,
        "event_mention_count": raw_metrics.event_mentions_created,
    }

    # Check conclusiveness
    inconclusive_reasons = []
    if raw_metrics.backward_compatibility_violations > 0:
        inconclusive_reasons.append(
            f"backward_compatibility_violations={raw_metrics.backward_compatibility_violations}"
        )
    if raw_metrics.entity_mentions_created == 0:
        inconclusive_reasons.append("no entity mentions created")
    if raw_metrics.event_mentions_created == 0:
        inconclusive_reasons.append("no event mentions created")

    return create_unified_report(
        metric_type="mention_layer_metrics",
        metrics=metrics_dict,
        run_metadata=run_metadata,
        determinism_pass=determinism_pass,
        feature_activation_evidence=feature_activation,
        inconclusive_reasons=inconclusive_reasons,
        evidence={
            "mention_types": {
                "entity_mentions": raw_metrics.entity_mentions_created,
                "event_mentions": raw_metrics.event_mentions_created,
            },
            "relationships": {
                "entity_refers_to": raw_metrics.entity_mentions_with_refers_to,
                "event_refers_to": raw_metrics.event_mentions_with_refers_to,
                "frame_instantiates": raw_metrics.frame_instantiates_event_mention,
            },
        },
    )
