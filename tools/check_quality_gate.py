"""CI quality gate: compares a current KG quality report against a stored baseline.

Exit codes:
  0 — quality is at or above baseline (within optional tolerance)
  1 — quality regressed beyond tolerance
  2 — usage / file-not-found error

Usage (in CI):
  python -m textgraphx.tools.check_quality_gate \\
      --baseline out/evaluation/baseline/kg_quality_report.json \\
      --current  out/evaluation/kg_quality_report.json \\
    --tolerance 0.02 \\
    --max-tlink-anchor-inconsistent-increase 0 \\
        --max-tlink-missing-anchor-metadata 0 \\
        --max-participation-in-frame-missing-increase 0 \\
        --max-participation-in-mention-missing-increase 0 \\
        --max-participation-in-frame-missing 0 \\
        --max-participation-in-mention-missing 0
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


def _runtime_total(report: dict, key: str, default: int = 0) -> int:
    """Extract a runtime diagnostics total from supported report shapes."""
    if key in report:
        try:
            return int(report[key])
        except (TypeError, ValueError):
            return default
    diagnostics = report.get("runtime_diagnostics", {})
    if isinstance(diagnostics, dict):
        totals = diagnostics.get("totals", {})
        if isinstance(totals, dict):
            try:
                return int(totals.get(key, default))
            except (TypeError, ValueError):
                return default
    return default


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
    parser.add_argument(
        "--max-tlink-anchor-inconsistent-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much tlink_anchor_inconsistent_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-tlink-missing-anchor-metadata",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for tlink_missing_anchor_metadata_count in the current report. "
            "Example: 0 requires complete anchor metadata coverage."
        ),
    )
    parser.add_argument(
        "--max-participation-in-frame-missing-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much participation_in_frame_missing_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-participation-in-mention-missing-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much participation_in_mention_missing_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-participation-in-frame-missing",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for participation_in_frame_missing_count in current report. "
            "Example: 0 requires no missing IN_FRAME aliases."
        ),
    )
    parser.add_argument(
        "--max-participation-in-mention-missing",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for participation_in_mention_missing_count in current report. "
            "Example: 0 requires no missing IN_MENTION aliases."
        ),
    )
    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline)
    current_path = Path(args.current)

    for p in (baseline_path, current_path):
        if not p.exists():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            return 2

    try:
        baseline_report = _load_report(baseline_path)
        current_report = _load_report(current_path)
        baseline_quality = _overall_quality(baseline_report)
        current_quality = _overall_quality(current_report)
    except (KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    threshold = baseline_quality - args.tolerance
    passed = current_quality >= threshold

    gate_reasons = []
    if not passed:
        gate_reasons.append("overall_quality")

    if args.max_tlink_anchor_inconsistent_increase is not None:
        base_inconsistent = _runtime_total(baseline_report, "tlink_anchor_inconsistent_count", 0)
        curr_inconsistent = _runtime_total(current_report, "tlink_anchor_inconsistent_count", 0)
        increase = curr_inconsistent - base_inconsistent
        inconsistent_ok = increase <= int(args.max_tlink_anchor_inconsistent_increase)
        if not inconsistent_ok:
            gate_reasons.append("tlink_anchor_inconsistent_increase")

    if args.max_tlink_missing_anchor_metadata is not None:
        curr_missing = _runtime_total(current_report, "tlink_missing_anchor_metadata_count", 0)
        missing_ok = curr_missing <= int(args.max_tlink_missing_anchor_metadata)
        if not missing_ok:
            gate_reasons.append("tlink_missing_anchor_metadata")

    if args.max_participation_in_frame_missing_increase is not None:
        base_missing = _runtime_total(baseline_report, "participation_in_frame_missing_count", 0)
        curr_missing = _runtime_total(current_report, "participation_in_frame_missing_count", 0)
        increase = curr_missing - base_missing
        frame_missing_inc_ok = increase <= int(args.max_participation_in_frame_missing_increase)
        if not frame_missing_inc_ok:
            gate_reasons.append("participation_in_frame_missing_increase")

    if args.max_participation_in_mention_missing_increase is not None:
        base_missing = _runtime_total(baseline_report, "participation_in_mention_missing_count", 0)
        curr_missing = _runtime_total(current_report, "participation_in_mention_missing_count", 0)
        increase = curr_missing - base_missing
        mention_missing_inc_ok = increase <= int(args.max_participation_in_mention_missing_increase)
        if not mention_missing_inc_ok:
            gate_reasons.append("participation_in_mention_missing_increase")

    if args.max_participation_in_frame_missing is not None:
        curr_missing = _runtime_total(current_report, "participation_in_frame_missing_count", 0)
        frame_missing_ok = curr_missing <= int(args.max_participation_in_frame_missing)
        if not frame_missing_ok:
            gate_reasons.append("participation_in_frame_missing")

    if args.max_participation_in_mention_missing is not None:
        curr_missing = _runtime_total(current_report, "participation_in_mention_missing_count", 0)
        mention_missing_ok = curr_missing <= int(args.max_participation_in_mention_missing)
        if not mention_missing_ok:
            gate_reasons.append("participation_in_mention_missing")

    passed = len(gate_reasons) == 0

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
        if args.max_tlink_anchor_inconsistent_increase is not None:
            base_inconsistent = _runtime_total(baseline_report, "tlink_anchor_inconsistent_count", 0)
            curr_inconsistent = _runtime_total(current_report, "tlink_anchor_inconsistent_count", 0)
            print(
                "[quality-gate] tlink_anchor_inconsistent_count "
                f"baseline={base_inconsistent} current={curr_inconsistent} "
                f"increase={curr_inconsistent - base_inconsistent} "
                f"max_increase={int(args.max_tlink_anchor_inconsistent_increase)}"
            )
        if args.max_tlink_missing_anchor_metadata is not None:
            curr_missing = _runtime_total(current_report, "tlink_missing_anchor_metadata_count", 0)
            print(
                "[quality-gate] tlink_missing_anchor_metadata_count "
                f"current={curr_missing} max_allowed={int(args.max_tlink_missing_anchor_metadata)}"
            )
        if args.max_participation_in_frame_missing_increase is not None:
            base_missing = _runtime_total(baseline_report, "participation_in_frame_missing_count", 0)
            curr_missing = _runtime_total(current_report, "participation_in_frame_missing_count", 0)
            print(
                "[quality-gate] participation_in_frame_missing_count "
                f"baseline={base_missing} current={curr_missing} "
                f"increase={curr_missing - base_missing} "
                f"max_increase={int(args.max_participation_in_frame_missing_increase)}"
            )
        if args.max_participation_in_mention_missing_increase is not None:
            base_missing = _runtime_total(baseline_report, "participation_in_mention_missing_count", 0)
            curr_missing = _runtime_total(current_report, "participation_in_mention_missing_count", 0)
            print(
                "[quality-gate] participation_in_mention_missing_count "
                f"baseline={base_missing} current={curr_missing} "
                f"increase={curr_missing - base_missing} "
                f"max_increase={int(args.max_participation_in_mention_missing_increase)}"
            )
        if args.max_participation_in_frame_missing is not None:
            curr_missing = _runtime_total(current_report, "participation_in_frame_missing_count", 0)
            print(
                "[quality-gate] participation_in_frame_missing_count "
                f"current={curr_missing} max_allowed={int(args.max_participation_in_frame_missing)}"
            )
        if args.max_participation_in_mention_missing is not None:
            curr_missing = _runtime_total(current_report, "participation_in_mention_missing_count", 0)
            print(
                "[quality-gate] participation_in_mention_missing_count "
                f"current={curr_missing} max_allowed={int(args.max_participation_in_mention_missing)}"
            )
        if gate_reasons:
            print(f"[quality-gate] reasons={','.join(gate_reasons)}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
