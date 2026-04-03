"""Evaluation metrics and graph-backed harness for KG quality tracking.

Iteration 4.13 starts with deterministic, testable metrics primitives and a
lightweight graph snapshot evaluator so quality can be measured in CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


def _safe_div(num: float, den: float) -> float:
    """Return num/den with a safe zero-denominator fallback."""
    return float(num) / float(den) if den else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Compute precision/recall/F1 from confusion-style counts."""
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * p * r, p + r)
    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "precision": p,
        "recall": r,
        "f1": f1,
    }


def coverage(processed: int, total: int) -> float:
    """Compute coverage ratio for processed units over total units."""
    return _safe_div(processed, total)


def macro_average(rows: Iterable[Dict[str, float]], key: str) -> float:
    """Compute simple macro-average of key across dict rows."""
    vals = [float(r.get(key, 0.0)) for r in rows]
    return _safe_div(sum(vals), len(vals))


def build_quality_report(
    dimension: str,
    tp: int,
    fp: int,
    fn: int,
    processed: int,
    total: int,
) -> Dict[str, Any]:
    """Build a stable quality report payload for one evaluation dimension."""
    return {
        "dimension": dimension,
        "metrics": precision_recall_f1(tp=tp, fp=fp, fn=fn),
        "coverage": {
            "processed": int(processed),
            "total": int(total),
            "coverage": coverage(processed=processed, total=total),
        },
    }


@dataclass
class GraphEvaluationHarness:
    """Evaluate coarse graph-quality indicators directly from Neo4j."""

    graph: Any

    def _count(self, cypher: str, params: Dict[str, Any] | None = None) -> int:
        rows = self.graph.run(cypher, params or {}).data()
        if not rows:
            return 0
        return int(rows[0].get("c", 0))

    def graph_count_snapshot(self) -> Dict[str, int]:
        """Return a stable graph-size snapshot used by integration checks."""
        return {
            "AnnotatedText": self._count("MATCH (n:AnnotatedText) RETURN count(n) AS c"),
            "Sentence": self._count("MATCH (n:Sentence) RETURN count(n) AS c"),
            "TagOccurrence": self._count("MATCH (n:TagOccurrence) RETURN count(n) AS c"),
            "NamedEntity": self._count("MATCH (n:NamedEntity) RETURN count(n) AS c"),
            "Entity": self._count("MATCH (n:Entity) RETURN count(n) AS c"),
            "TEvent": self._count("MATCH (n:TEvent) RETURN count(n) AS c"),
            "TIMEX": self._count("MATCH (n:TIMEX) RETURN count(n) AS c"),
            "TLINK": self._count("MATCH ()-[r:TLINK]->() RETURN count(r) AS c"),
        }

    def temporal_coverage_report(self) -> Dict[str, Any]:
        """Build a coarse temporal-quality report from current graph state."""
        s = self.graph_count_snapshot()
        # Coarse proxy: temporal artifacts should be attached to processed docs.
        processed = s["TEvent"] + s["TIMEX"]
        total = max(1, s["AnnotatedText"])
        return build_quality_report(
            dimension="temporal",
            tp=s["TEvent"],
            fp=0,
            fn=0,
            processed=processed,
            total=total,
        )

    def entity_coverage_report(self) -> Dict[str, Any]:
        """Build a coarse entity-quality report from current graph state."""
        s = self.graph_count_snapshot()
        processed = s["Entity"]
        total = max(1, s["NamedEntity"])
        return build_quality_report(
            dimension="entity",
            tp=s["Entity"],
            fp=0,
            fn=max(0, s["NamedEntity"] - s["Entity"]),
            processed=processed,
            total=total,
        )
