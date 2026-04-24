"""CI quality gate: compares a current KG quality report against a stored baseline.

Exit codes:
  0 — quality is at or above baseline (within optional tolerance)
  1 — quality regressed beyond tolerance
  2 — usage / file-not-found error

Usage (in CI):
  python -m textgraphx.tools.check_quality_gate \\
    --baseline src/textgraphx/datastore/evaluation/baseline/kg_quality_report.json \\
      --current  out/evaluation/kg_quality_report.json \\
    --tolerance 0.02 \\
    --max-tlink-anchor-inconsistent-increase 0 \\
        --max-tlink-reciprocal-cycle-increase 0 \
        --max-documents-with-temporal-connectivity-gaps-increase 0 \
        --max-tlink-missing-anchor-metadata 0 \\
        --max-participation-in-frame-missing-increase 0 \\
        --max-participation-in-mention-missing-increase 0 \\
        --max-participation-in-frame-missing 0 \\
        --max-participation-in-mention-missing 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from textgraphx.evaluation.quality import (
    compare_reports,
    load_quality_report,
    overall_quality_from_report,
    runtime_total_from_report,
)


def _load_report(path: Path) -> dict:
    return load_quality_report(path)


def _overall_quality(report: dict) -> float:
    """Extract overall_quality from supported report shapes."""
    return overall_quality_from_report(report)


def _runtime_total(report: dict, key: str, default: int = 0) -> int:
    """Extract a runtime diagnostics total from supported report shapes."""
    return runtime_total_from_report(report, key, default)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare KG quality report against a stored baseline.",
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to the baseline JSON (e.g. src/textgraphx/datastore/evaluation/baseline/kg_quality_report.json).",
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
        "--max-tlink-reciprocal-cycle-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much tlink_reciprocal_cycle_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-isolated-temporal-anchor-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much isolated_temporal_anchor_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-documents-with-temporal-connectivity-gaps-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much documents_with_temporal_connectivity_gaps_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
        ),
    )
    parser.add_argument(
        "--max-documents-without-temporal-tlinks-increase",
        type=int,
        default=None,
        help=(
            "Optional cap on how much documents_without_temporal_tlinks_count may increase "
            "relative to baseline. Example: 0 means no increase allowed."
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
    parser.add_argument(
        "--max-timexmention-missing-doc-id",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for timexmention_missing_doc_id_count in current report. "
            "Example: 0 requires all TimexMention nodes to carry doc_id."
        ),
    )
    parser.add_argument(
        "--max-timexmention-missing-span-coordinates",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for timexmention_missing_span_coordinates_count in current report. "
            "Example: 0 requires all TimexMention nodes to have start_tok/end_tok."
        ),
    )
    parser.add_argument(
        "--max-timexmention-broken-refers-to",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for timexmention_broken_refers_to_count in current report. "
            "Example: 0 requires all TimexMention nodes to REFERS_TO a TIMEX node."
        ),
    )
    parser.add_argument(
        "--max-dct-timexmention-count",
        type=int,
        default=None,
        help=(
            "Optional absolute cap for dct_timexmention_count in current report. "
            "Example: 0 enforces DCT metadata exemption (no TimexMention for DCT)."
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
        comparison = compare_reports(baseline_report, current_report, tolerance=args.tolerance)
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

    if args.max_tlink_reciprocal_cycle_increase is not None:
        base_cycles = _runtime_total(baseline_report, "tlink_reciprocal_cycle_count", 0)
        curr_cycles = _runtime_total(current_report, "tlink_reciprocal_cycle_count", 0)
        increase = curr_cycles - base_cycles
        cycle_ok = increase <= int(args.max_tlink_reciprocal_cycle_increase)
        if not cycle_ok:
            gate_reasons.append("tlink_reciprocal_cycle_increase")

    if args.max_isolated_temporal_anchor_increase is not None:
        base_isolated = _runtime_total(baseline_report, "isolated_temporal_anchor_count", 0)
        curr_isolated = _runtime_total(current_report, "isolated_temporal_anchor_count", 0)
        increase = curr_isolated - base_isolated
        isolated_ok = increase <= int(args.max_isolated_temporal_anchor_increase)
        if not isolated_ok:
            gate_reasons.append("isolated_temporal_anchor_increase")

    if args.max_documents_with_temporal_connectivity_gaps_increase is not None:
        base_docs = _runtime_total(baseline_report, "documents_with_temporal_connectivity_gaps_count", 0)
        curr_docs = _runtime_total(current_report, "documents_with_temporal_connectivity_gaps_count", 0)
        increase = curr_docs - base_docs
        docs_ok = increase <= int(args.max_documents_with_temporal_connectivity_gaps_increase)
        if not docs_ok:
            gate_reasons.append("documents_with_temporal_connectivity_gaps_increase")

    if args.max_documents_without_temporal_tlinks_increase is not None:
        base_docs = _runtime_total(baseline_report, "documents_without_temporal_tlinks_count", 0)
        curr_docs = _runtime_total(current_report, "documents_without_temporal_tlinks_count", 0)
        increase = curr_docs - base_docs
        docs_ok = increase <= int(args.max_documents_without_temporal_tlinks_increase)
        if not docs_ok:
            gate_reasons.append("documents_without_temporal_tlinks_increase")

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

    if args.max_timexmention_missing_doc_id is not None:
        curr_missing = _runtime_total(current_report, "timexmention_missing_doc_id_count", 0)
        timex_doc_ok = curr_missing <= int(args.max_timexmention_missing_doc_id)
        if not timex_doc_ok:
            gate_reasons.append("timexmention_missing_doc_id")

    if args.max_timexmention_missing_span_coordinates is not None:
        curr_missing = _runtime_total(current_report, "timexmention_missing_span_coordinates_count", 0)
        timex_span_ok = curr_missing <= int(args.max_timexmention_missing_span_coordinates)
        if not timex_span_ok:
            gate_reasons.append("timexmention_missing_span_coordinates")

    if args.max_timexmention_broken_refers_to is not None:
        curr_missing = _runtime_total(current_report, "timexmention_broken_refers_to_count", 0)
        timex_chain_ok = curr_missing <= int(args.max_timexmention_broken_refers_to)
        if not timex_chain_ok:
            gate_reasons.append("timexmention_broken_refers_to")

    if args.max_dct_timexmention_count is not None:
        curr_count = _runtime_total(current_report, "dct_timexmention_count", 0)
        dct_ok = curr_count <= int(args.max_dct_timexmention_count)
        if not dct_ok:
            gate_reasons.append("dct_timexmention_count")

    passed = len(gate_reasons) == 0

    label = "PASS" if passed else "FAIL"
    print(
        f"[quality-gate] {label} | "
        f"baseline={baseline_quality:.4f}  current={current_quality:.4f}  "
        f"threshold={threshold:.4f}  tolerance={args.tolerance:.4f}"
    )

    if args.verbose:
        delta = comparison["overall_quality_delta"]
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
        if args.max_tlink_reciprocal_cycle_increase is not None:
            base_cycles = _runtime_total(baseline_report, "tlink_reciprocal_cycle_count", 0)
            curr_cycles = _runtime_total(current_report, "tlink_reciprocal_cycle_count", 0)
            print(
                "[quality-gate] tlink_reciprocal_cycle_count "
                f"baseline={base_cycles} current={curr_cycles} "
                f"increase={curr_cycles - base_cycles} "
                f"max_increase={int(args.max_tlink_reciprocal_cycle_increase)}"
            )
        if args.max_isolated_temporal_anchor_increase is not None:
            base_isolated = _runtime_total(baseline_report, "isolated_temporal_anchor_count", 0)
            curr_isolated = _runtime_total(current_report, "isolated_temporal_anchor_count", 0)
            print(
                "[quality-gate] isolated_temporal_anchor_count "
                f"baseline={base_isolated} current={curr_isolated} "
                f"increase={curr_isolated - base_isolated} "
                f"max_increase={int(args.max_isolated_temporal_anchor_increase)}"
            )
        if args.max_documents_with_temporal_connectivity_gaps_increase is not None:
            base_docs = _runtime_total(baseline_report, "documents_with_temporal_connectivity_gaps_count", 0)
            curr_docs = _runtime_total(current_report, "documents_with_temporal_connectivity_gaps_count", 0)
            print(
                "[quality-gate] documents_with_temporal_connectivity_gaps_count "
                f"baseline={base_docs} current={curr_docs} "
                f"increase={curr_docs - base_docs} "
                f"max_increase={int(args.max_documents_with_temporal_connectivity_gaps_increase)}"
            )
        if args.max_documents_without_temporal_tlinks_increase is not None:
            base_docs = _runtime_total(baseline_report, "documents_without_temporal_tlinks_count", 0)
            curr_docs = _runtime_total(current_report, "documents_without_temporal_tlinks_count", 0)
            print(
                "[quality-gate] documents_without_temporal_tlinks_count "
                f"baseline={base_docs} current={curr_docs} "
                f"increase={curr_docs - base_docs} "
                f"max_increase={int(args.max_documents_without_temporal_tlinks_increase)}"
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
        if args.max_timexmention_missing_doc_id is not None:
            curr_missing = _runtime_total(current_report, "timexmention_missing_doc_id_count", 0)
            print(
                "[quality-gate] timexmention_missing_doc_id_count "
                f"current={curr_missing} max_allowed={int(args.max_timexmention_missing_doc_id)}"
            )
        if args.max_timexmention_missing_span_coordinates is not None:
            curr_missing = _runtime_total(current_report, "timexmention_missing_span_coordinates_count", 0)
            print(
                "[quality-gate] timexmention_missing_span_coordinates_count "
                f"current={curr_missing} max_allowed={int(args.max_timexmention_missing_span_coordinates)}"
            )
        if args.max_timexmention_broken_refers_to is not None:
            curr_missing = _runtime_total(current_report, "timexmention_broken_refers_to_count", 0)
            print(
                "[quality-gate] timexmention_broken_refers_to_count "
                f"current={curr_missing} max_allowed={int(args.max_timexmention_broken_refers_to)}"
            )
        if args.max_dct_timexmention_count is not None:
            curr_count = _runtime_total(current_report, "dct_timexmention_count", 0)
            print(
                "[quality-gate] dct_timexmention_count "
                f"current={curr_count} max_allowed={int(args.max_dct_timexmention_count)}"
            )
        if gate_reasons:
            print(f"[quality-gate] reasons={','.join(gate_reasons)}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
