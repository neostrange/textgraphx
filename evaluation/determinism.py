"""Determinism verification for evaluation runs.

Compares repeated runs under identical conditions to validate reproducibility.
Identifies configuration or randomness sources that violate reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DeterminismViolation:
    """A detected deviation between two supposedly identical runs."""

    run1_name: str
    run2_name: str
    metric_name: str
    value1: Any
    value2: Any
    absolute_diff: Optional[float] = None
    relative_diff_percent: Optional[float] = None

    def __str__(self) -> str:
        msg = f"{self.metric_name}: {self.value1} vs {self.value2}"
        if self.absolute_diff is not None:
            msg += f" (diff={self.absolute_diff})"
        if self.relative_diff_percent is not None:
            msg += f" ({self.relative_diff_percent:.1f}%)"
        return msg


@dataclass
class DeterminismReport:
    """Results of comparing two runs for determinism."""

    conclusive: bool
    num_violations: int
    violations: List[DeterminismViolation]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for embedding in validity header."""
        return {
            "conclusive": self.conclusive,
            "num_violations": self.num_violations,
            "violations": [
                {
                    "run1_name": v.run1_name,
                    "run2_name": v.run2_name,
                    "metric_name": v.metric_name,
                    "value1": v.value1,
                    "value2": v.value2,
                    "absolute_diff": v.absolute_diff,
                    "relative_diff_percent": v.relative_diff_percent,
                }
                for v in self.violations
            ],
            "summary": self.summary,
        }


def compare_metric_results(
    results1: Dict[str, Any],
    results2: Dict[str, Any],
    tolerance: float = 0.0,
) -> DeterminismReport:
    """Compare two metric result dicts for consistency.

    Args:
        results1: Metric results from run 1
        results2: Metric results from run 2
        tolerance: Fractional tolerance for numeric comparisons (default: 0.0 = exact match)

    Returns:
        DeterminismReport with detected violations (empty if deterministic)
    """
    violations = []

    all_keys = set(results1.keys()) | set(results2.keys())
    for key in sorted(all_keys):
        if key not in results1:
            violations.append(
                DeterminismViolation(
                    run1_name="run1",
                    run2_name="run2",
                    metric_name=key,
                    value1=None,
                    value2=results2[key],
                )
            )
        elif key not in results2:
            violations.append(
                DeterminismViolation(
                    run1_name="run1",
                    run2_name="run2",
                    metric_name=key,
                    value1=results1[key],
                    value2=None,
                )
            )
        else:
            v1 = results1[key]
            v2 = results2[key]
            if _values_differ(v1, v2, tolerance):
                abs_diff = None
                rel_diff = None
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    abs_diff = abs(v1 - v2)
                    if v1 != 0:
                        rel_diff = 100.0 * abs_diff / abs(v1)
                violations.append(
                    DeterminismViolation(
                        run1_name="run1",
                        run2_name="run2",
                        metric_name=key,
                        value1=v1,
                        value2=v2,
                        absolute_diff=abs_diff,
                        relative_diff_percent=rel_diff,
                    )
                )

    conclusive = len(violations) == 0
    summary = (
        "Deterministic"
        if conclusive
        else f"Non-deterministic: {len(violations)} metric(s) differ"
    )

    return DeterminismReport(
        conclusive=conclusive,
        num_violations=len(violations),
        violations=violations,
        summary=summary,
    )


def _values_differ(v1: Any, v2: Any, tolerance: float) -> bool:
    """Check if two values differ beyond tolerance."""
    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        if tolerance > 0:
            return abs(v1 - v2) > tolerance * max(abs(v1), abs(v2))
        else:
            return v1 != v2
    elif isinstance(v1, (list, tuple)) and isinstance(v2, (list, tuple)):
        if len(v1) != len(v2):
            return True
        return any(_values_differ(a, b, tolerance) for a, b in zip(v1, v2))
    elif isinstance(v1, dict) and isinstance(v2, dict):
        if set(v1.keys()) != set(v2.keys()):
            return True
        return any(_values_differ(v1[k], v2[k], tolerance) for k in v1)
    else:
        return v1 != v2
