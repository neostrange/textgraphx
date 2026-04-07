"""Checkpoint helpers for per-document pipeline resume support.

This module stores lightweight phase checkpoints as JSON files under:
  <output_dir>/checkpoints/<doc_id>/<phase>.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    from textgraphx.time_utils import utc_iso_now
except ImportError:  # pragma: no cover - support script-style execution
    from time_utils import utc_iso_now


@dataclass
class CheckpointSummary:
    """Computed resume plan from available checkpoints."""

    doc_id: str
    completed_phases: List[str]
    remaining_phases: List[str]
    resume_from_phase: Optional[str]


class CheckpointManager:
    """Manage JSON checkpoints for phase-level pipeline execution state."""

    DEFAULT_NODE_LABELS = [
        "AnnotatedText",
        "Sentence",
        "TagOccurrence",
        "TIMEX",
        "TEvent",
        "EventMention",
    ]
    DEFAULT_EDGE_TYPES = [
        "CONTAINS_SENTENCE",
        "HAS_TOKEN",
        "TRIGGERS",
        "DESCRIBES",
        "FRAME_DESCRIBES_EVENT",
        "TLINK",
    ]

    def __init__(self, base_dir: str = "out/checkpoints"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_doc_id(doc_id: str) -> str:
        return str(doc_id).replace("/", "_").replace("\\", "_").replace(":", "_")

    def _checkpoint_path(self, doc_id: str, phase_name: str) -> Path:
        safe_doc = self._safe_doc_id(doc_id)
        return self.base_dir / safe_doc / f"{phase_name}.json"

    def save_checkpoint(
        self,
        doc_id: str,
        phase_name: str,
        node_counts: Optional[Dict[str, int]] = None,
        edge_counts: Optional[Dict[str, int]] = None,
        phase_markers: Optional[List[str]] = None,
        properties_snapshot: Optional[Dict[str, object]] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> Path:
        """Write a phase checkpoint JSON file and return its path."""
        path = self._checkpoint_path(doc_id, phase_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "doc_id": str(doc_id),
            "phase": str(phase_name),
            "timestamp": utc_iso_now(),
            "node_counts": node_counts or {},
            "edge_counts": edge_counts or {},
            "phase_markers": phase_markers or [],
            "properties_snapshot": properties_snapshot or {},
            "metadata": metadata or {},
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return path

    def load_checkpoint(self, doc_id: str, phase_name: str) -> Optional[Dict[str, object]]:
        """Load a single checkpoint file if present."""
        path = self._checkpoint_path(doc_id, phase_name)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def list_completed_phases(self, doc_id: str, phase_order: List[str]) -> List[str]:
        """Return completed phases (in canonical order) for a document."""
        completed: List[str] = []
        for phase in phase_order:
            payload = self.load_checkpoint(doc_id, phase)
            if payload is not None:
                completed.append(phase)
        return completed

    def validate_checkpoint(
        self,
        checkpoint: Dict[str, object],
        expected_doc_id: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
        min_node_counts: Optional[Dict[str, int]] = None,
        min_edge_counts: Optional[Dict[str, int]] = None,
    ) -> bool:
        """Validate key checkpoint integrity constraints."""
        if expected_doc_id is not None and str(checkpoint.get("doc_id")) != str(expected_doc_id):
            return False
        if allowed_phases is not None and str(checkpoint.get("phase")) not in set(allowed_phases):
            return False

        node_counts = checkpoint.get("node_counts") or {}
        edge_counts = checkpoint.get("edge_counts") or {}

        for label, minimum in (min_node_counts or {}).items():
            if int(node_counts.get(label, 0)) < int(minimum):
                return False
        for rel, minimum in (min_edge_counts or {}).items():
            if int(edge_counts.get(rel, 0)) < int(minimum):
                return False
        return True

    def resume_from_checkpoint(self, doc_id: str, phase_order: List[str]) -> CheckpointSummary:
        """Compute which phases are done and which remain."""
        completed = self.list_completed_phases(doc_id, phase_order)
        if not completed:
            return CheckpointSummary(
                doc_id=str(doc_id),
                completed_phases=[],
                remaining_phases=list(phase_order),
                resume_from_phase=phase_order[0] if phase_order else None,
            )

        last_completed_idx = max(phase_order.index(phase) for phase in completed)
        remaining = phase_order[last_completed_idx + 1 :]
        resume_from = remaining[0] if remaining else None
        return CheckpointSummary(
            doc_id=str(doc_id),
            completed_phases=completed,
            remaining_phases=remaining,
            resume_from_phase=resume_from,
        )

    def capture_graph_counts(
        self,
        graph,
        node_labels: Optional[List[str]] = None,
        edge_types: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, int]]:
        """Capture lightweight node/edge count snapshots from Neo4j."""
        node_counts: Dict[str, int] = {}
        edge_counts: Dict[str, int] = {}

        for label in (node_labels or self.DEFAULT_NODE_LABELS):
            rows = graph.run(f"MATCH (n:{label}) RETURN count(n) AS c").data()
            node_counts[label] = int(rows[0].get("c", 0)) if rows else 0

        for rel in (edge_types or self.DEFAULT_EDGE_TYPES):
            rows = graph.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").data()
            edge_counts[rel] = int(rows[0].get("c", 0)) if rows else 0

        return {
            "node_counts": node_counts,
            "edge_counts": edge_counts,
        }
