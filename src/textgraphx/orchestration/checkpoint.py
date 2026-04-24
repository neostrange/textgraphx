import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class CheckpointSummary:
    completed_phases: List[str]
    remaining_phases: List[str]
    resume_from_phase: Optional[str]


class CheckpointManager:
    def __init__(self, base_dir: str = "out/checkpoints"):
        self.base_dir = Path(base_dir)

    def save_checkpoint(
        self,
        doc_id: str,
        phase_name: str,
        node_counts: Dict[str, int] = None,
        edge_counts: Dict[str, int] = None,
        phase_markers: List[str] = None,
        properties_snapshot: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> Path:
        """Save a checkpoint of the current graph state."""
        doc_dir = self.base_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = doc_dir / f"{phase_name}.json"

        payload = {
            "doc_id": doc_id,
            "phase": phase_name,
            "node_counts": node_counts or {},
            "edge_counts": edge_counts or {},
            "phase_markers": phase_markers or [],
            "properties_snapshot": properties_snapshot or {},
            "metadata": metadata or {},
        }

        with open(checkpoint_path, "w") as f:
            json.dump(payload, f, indent=2)

        return checkpoint_path

    def load_checkpoint(self, doc_id: str, phase_name: str) -> Optional[Dict[str, Any]]:
        checkpoint_path = self.base_dir / doc_id / f"{phase_name}.json"
        if not checkpoint_path.exists():
            return None

        with open(checkpoint_path, "r") as f:
            return json.load(f)

    def validate_checkpoint(
        self,
        payload: dict,
        expected_doc_id: str = None,
        allowed_phases: list = None,
        min_node_counts: dict = None,
        min_edge_counts: dict = None,
    ) -> bool:
        if not payload:
            return False

        if expected_doc_id and payload.get("doc_id") != expected_doc_id:
            return False

        if allowed_phases and payload.get("phase") not in allowed_phases:
            return False

        if min_node_counts:
            actual_node_counts = payload.get("node_counts", {})
            for key, min_val in min_node_counts.items():
                if actual_node_counts.get(key, 0) < min_val:
                    return False

        if min_edge_counts:
            actual_edge_counts = payload.get("edge_counts", {})
            for key, min_val in min_edge_counts.items():
                if actual_edge_counts.get(key, 0) < min_val:
                    return False

        return True

    def resume_from_checkpoint(self, doc_id: str, phase_order: List[str]) -> CheckpointSummary:
        completed = []
        remaining = list(phase_order)

        for phase in phase_order:
            if self.load_checkpoint(doc_id, phase) is not None:
                completed.append(phase)
                remaining.remove(phase)
            else:
                break

        resume_from = remaining[0] if remaining else None
        return CheckpointSummary(
            completed_phases=completed,
            remaining_phases=remaining,
            resume_from_phase=resume_from,
        )