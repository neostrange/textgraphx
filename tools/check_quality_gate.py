"""CI quality gate: compares a current KG quality report against a stored baseline.

Exit codes:
  0 — quality is at or above baseline (within optional tolerance)
  1 — quality regressed beyond tolerance
  2 — usage / file-not-found error

Usage (in CI):
  python -m textgraphx.tools.check_quality_gate \\
      --baseline out/evaluation/baseline/kg_quality_report.json \\
      --current  out/evaluation/kg_quality_report.json \\
      --tolerance 0.02
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_report(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def _overall_quality(report: dict) -> float:
    """Extract overall_quality from either a summary dict or a full report object."""
    if "overall_quality" in report:
        return float(report["overall_quality"])
    # FullStackEvaluator JSON shape: {"suite": {...}, ...} or list of phase reports
    # Attempt nested lookup for known harness export shapes.
    for key in ("suite", "report", "result"):
        if key in report and isinstance(report[key], dict):
            v = report[key].get("overall_quality")
            if v is not None:
                return float(v)
    raise KeyError(
        "Cannot locate 'overall_quality' in report. "
        "Run evaluate_kg_quality with --json to produce a compatible report."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare KG quality report against a stored baseline.",
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to the baseline JSON (e.g. out/evaluation/baseline/kg_quality_report.json).",
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Path to the current-run JSON report.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help=(
            "Allowed regression below baseline before gate fails. "
            "E.g. 0.02 allows up to 2 percentage-point drop. Default: 0.0 (strict)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
    )
    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline)
    current_path = Path(args.current)

    for p in (baseline_path, current_path):
        if not p.exists():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            return 2

    try:
        baseline_quality = _overall_quality(_load_report(baseline_path))
        current_quality = _overall_quality(_load_report(current_path))
    except (KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    threshold = baseline_quality - args.tolerance
    passed = current_quality >= threshold

    label = "PASS" if passed else "FAIL"
    print(
        f"[quality-gate] {label} | "
        f"baseline={baseline_quality:.4f}  current={current_quality:.4f}  "
        f"threshold={threshold:.4f}  tolerance={args.tolerance:.4f}"
    )

    if args.verbose:
        delta = current_quality - baseline_quality
        sign = "+" if delta >= 0 else ""
        print(f"[quality-gate] delta={sign}{delta:.4f}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
