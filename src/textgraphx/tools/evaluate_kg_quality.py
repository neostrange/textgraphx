"""CLI for KG quality evaluation using the unified full-stack harness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from textgraphx.evaluation.quality import (
    compare_reports,
    generate_quality_report,
    identify_regression,
    load_quality_report,
)
from textgraphx.evaluation.report_validity import RunMetadata, compute_config_hash, compute_dataset_hash
from textgraphx.reasoning.temporal.time import utc_iso_now


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run full-stack KG quality evaluation and export reports.",
    )
    parser.add_argument(
        "--dataset-dir",
        required=True,
        help="Directory containing dataset/gold files used for dataset hashing context.",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Optional cap for number of dataset files (sorted) to evaluate; 0 means all files.",
    )
    parser.add_argument(
        "--output-dir",
        default="out/evaluation",
        help="Directory where reports will be written.",
    )
    parser.add_argument(
        "--snapshot-kind",
        choices=["current", "baseline"],
        default="current",
        help="Machine-readable label for the emitted report (current run or accepted baseline snapshot).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed metadata for reproducibility headers.",
    )
    parser.add_argument(
        "--strict-gate",
        action="store_true",
        default=False,
        help="Mark strict transition gate as enabled in run metadata.",
    )
    parser.add_argument(
        "--fusion-enabled",
        action="store_true",
        default=False,
        help="Mark cross-document fusion as enabled in run metadata.",
    )
    parser.add_argument(
        "--cleanup-mode",
        choices=["auto", "none", "full"],
        default="auto",
        help="Cleanup mode metadata for run validity headers.",
    )
    parser.add_argument(
        "--determinism-pass",
        choices=["auto", "pass", "fail"],
        default="auto",
        help="Optional determinism flag override for validity headers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Export JSON report.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        default=False,
        help="Export CSV report.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        default=False,
        help="Export Markdown report.",
    )
    parser.add_argument(
        "--baseline-report",
        default=None,
        help="Optional baseline JSON report to compare against the current run.",
    )
    parser.add_argument(
        "--comparison-json",
        default=None,
        help="Optional path for writing a baseline-vs-current comparison JSON payload.",
    )
    return parser


def _dataset_files(dataset_dir: Path, max_docs: int = 0) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.xml", "*.naf", "*.txt"):
        files.extend(sorted(dataset_dir.glob(pattern)))
    selected = sorted(set(files))
    if max_docs and max_docs > 0:
        return selected[: max(1, int(max_docs))]
    return selected


def _quality_tier(overall_quality: float) -> str:
    if overall_quality >= 0.90:
        return "PRODUCTION_READY"
    if overall_quality >= 0.80:
        return "ACCEPTABLE"
    if overall_quality >= 0.70:
        return "NEEDS_WORK"
    return "RESEARCH_PHASE"


def _determinism_flag(mode: str):
    if mode == "pass":
        return True
    if mode == "fail":
        return False
    return None


def _config_to_hashable_dict(cfg) -> dict:
    return {
        "runtime": {
            "mode": getattr(cfg.runtime, "mode", "production"),
            "strict_transition_gate": getattr(cfg.runtime, "strict_transition_gate", None),
            "enable_cross_document_fusion": getattr(cfg.runtime, "enable_cross_document_fusion", False),
        },
        "services": {
            "temporal_url": getattr(cfg.services, "temporal_url", ""),
            "coref_url": getattr(cfg.services, "coref_url", ""),
            "srl_url": getattr(cfg.services, "srl_url", ""),
        },
    }


def _ensure_any_export_requested(args) -> tuple[bool, bool, bool]:
    # Default behavior exports all formats when none explicitly selected.
    if not (args.json or args.csv or args.markdown):
        return True, True, True
    return args.json, args.csv, args.markdown


def _build_operator_summary(summary: dict) -> str | None:
    """Build concise operator summary without affecting JSON stdout payload."""
    if not isinstance(summary, dict):
        return None
    required = (
        "tlink_anchor_inconsistent_count",
        "tlink_anchor_self_link_count",
        "tlink_anchor_endpoint_violation_count",
        "tlink_anchor_filter_suppressed_count",
        "tlink_missing_anchor_metadata_count",
        "tlink_reciprocal_cycle_count",
        "documents_with_temporal_connectivity_gaps_count",
        "documents_without_temporal_tlinks_count",
    )
    if not all(k in summary for k in required):
        return None
    return (
        "KG quality operator summary: "
        f"quality={summary.get('overall_quality', 0.0):.4f} "
        f"tier={summary.get('quality_tier', 'UNKNOWN')} "
        f"tlink_anchor_inconsistent={int(summary.get('tlink_anchor_inconsistent_count', 0))} "
        f"self_links={int(summary.get('tlink_anchor_self_link_count', 0))} "
        f"endpoint_violations={int(summary.get('tlink_anchor_endpoint_violation_count', 0))} "
        f"anchor_suppressed={int(summary.get('tlink_anchor_filter_suppressed_count', 0))} "
        f"missing_anchor_metadata={int(summary.get('tlink_missing_anchor_metadata_count', 0))} "
        f"reciprocal_cycles={int(summary.get('tlink_reciprocal_cycle_count', 0))} "
        f"connectivity_gap_docs={int(summary.get('documents_with_temporal_connectivity_gaps_count', 0))} "
        f"docs_without_temporal_tlinks={int(summary.get('documents_without_temporal_tlinks_count', 0))}"
    )


def _format_delta(value: float) -> str:
    rounded = round(float(value), 4)
    if rounded.is_integer():
        return f"{int(rounded):+d}"
    return f"{rounded:+.4f}"


def _build_temporal_comparison_summary(comparison: dict) -> str | None:
    """Build concise temporal regression-driver summary for stderr output."""
    if not isinstance(comparison, dict):
        return None

    temporal_score_delta = comparison.get("section_deltas", {}).get("temporal")
    temporal_details = comparison.get("temporal_delta_details", {})
    if temporal_score_delta is None or not isinstance(temporal_details, dict):
        return None

    top_drivers = []
    driver_label_map = {
        "tlink_conflict_count": "conflicts",
        "tlink_anchor_inconsistent_count": "anchor_inconsistent",
        "tlink_anchor_self_link_count": "self_links",
        "tlink_anchor_endpoint_violation_count": "endpoint_violations",
        "tlink_anchor_filter_suppressed_count": "anchor_suppressed",
        "tlink_missing_anchor_metadata_count": "missing_anchor_metadata",
    }
    for key, label in driver_label_map.items():
        delta = float(temporal_details.get(key, 0.0) or 0.0)
        if delta > 0:
            top_drivers.append((delta, label))
    top_drivers.sort(key=lambda item: (-item[0], item[1]))

    return (
        "KG temporal comparison: "
        f"temporal_score_delta={_format_delta(float(temporal_score_delta or 0.0))} "
        f"issue_delta={_format_delta(float(temporal_details.get('temporal_issue_count', 0.0) or 0.0))} "
        f"reciprocal_cycles={_format_delta(float(temporal_details.get('tlink_reciprocal_cycle_count', 0.0) or 0.0))} "
        f"isolated_anchors={_format_delta(float(temporal_details.get('isolated_temporal_anchor_count', 0.0) or 0.0))} "
        f"connectivity_gap_docs={_format_delta(float(temporal_details.get('documents_with_temporal_connectivity_gaps_count', 0.0) or 0.0))} "
        f"docs_without_temporal_tlinks={_format_delta(float(temporal_details.get('documents_without_temporal_tlinks_count', 0.0) or 0.0))} "
        f"top_drivers={','.join(f'{label}:{_format_delta(delta)}' for delta, label in top_drivers[:3]) or 'none'}"
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(payload, fh, indent=2)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _portable_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _current_git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    commit = result.stdout.strip() if result.returncode == 0 else ""
    return commit or "unknown"


def _capture_timestamp() -> str:
    return utc_iso_now().replace("+00:00", "Z")


def _build_run_metadata(*, args, dataset_paths: list[Path], config_dict: dict, timestamp: str) -> dict:
    return RunMetadata(
        dataset_hash=compute_dataset_hash(dataset_paths),
        config_hash=compute_config_hash(config_dict),
        seed=int(args.seed),
        strict_gate_enabled=bool(args.strict_gate),
        fusion_enabled=bool(args.fusion_enabled),
        cleanup_mode=str(args.cleanup_mode),
        timestamp=timestamp,
    ).to_dict()


def _build_capture_metadata(*, args, repo_root: Path, dataset_dir: Path, output_dir: Path, documents: int) -> dict:
    metadata = {
        "snapshot_kind": str(args.snapshot_kind),
        "git_commit": _current_git_commit(repo_root),
        "dataset_dir": _portable_path(dataset_dir, repo_root),
        "output_dir": _portable_path(output_dir, repo_root),
        "document_count": int(documents),
        "max_docs": int(args.max_docs or 0),
    }
    if args.baseline_report:
        metadata["baseline_report"] = _portable_path(Path(args.baseline_report), repo_root)
        comparison_path = Path(args.comparison_json) if args.comparison_json else output_dir / "kg_quality_comparison.json"
        metadata["comparison_json"] = _portable_path(comparison_path, repo_root)
    return metadata


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    dataset_dir = Path(args.dataset_dir)
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise ValueError(f"Dataset directory not found: {dataset_dir}")

    dataset_paths = _dataset_files(dataset_dir, max_docs=int(args.max_docs or 0))
    if not dataset_paths:
        raise ValueError(f"No dataset files found in: {dataset_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_root = _repo_root()

    from textgraphx.infrastructure.config import get_config
    from textgraphx.database.client import make_graph_from_config
    from textgraphx.evaluation.fullstack_harness import FullStackEvaluator

    cfg = get_config()
    config_dict = _config_to_hashable_dict(cfg)
    baseline_report = load_quality_report(args.baseline_report) if args.baseline_report else None
    report_timestamp = _capture_timestamp()
    run_metadata = _build_run_metadata(
        args=args,
        dataset_paths=dataset_paths,
        config_dict=config_dict,
        timestamp=report_timestamp,
    )
    capture_metadata = _build_capture_metadata(
        args=args,
        repo_root=repo_root,
        dataset_dir=dataset_dir,
        output_dir=output_dir,
        documents=len(dataset_paths),
    )

    graph = make_graph_from_config()
    try:
        evaluator = FullStackEvaluator(
            graph=graph,
            dataset_paths=dataset_paths,
            config_dict=config_dict,
            seed=int(args.seed),
            strict_gate_enabled=bool(args.strict_gate),
            fusion_enabled=bool(args.fusion_enabled),
            cleanup_mode=str(args.cleanup_mode),
        )

        suite = evaluator.evaluate(determinism_pass=_determinism_flag(args.determinism_pass))

        report = generate_quality_report(
            runtime_diagnostics=suite.runtime_diagnostics,
            evaluation_suite=suite,
            documents=len(dataset_paths),
            timestamp=report_timestamp,
            run_metadata=run_metadata,
            capture_metadata=capture_metadata,
        )

        export_json, export_csv, export_md = _ensure_any_export_requested(args)
        if export_json:
            _write_json(output_dir / "kg_quality_report.json", report)
        if export_csv:
            evaluator.export_csv(suite, output_dir / "kg_quality_scores.csv")
        if export_md:
            evaluator.export_markdown(suite, output_dir / "kg_quality_report.md")

        if baseline_report is not None:
            comparison = compare_reports(baseline_report, report)
            regression, reasons = identify_regression(baseline_report, report)
            report["comparison"] = comparison
            report["regression_detected"] = regression
            report["regression_reasons"] = reasons
            comparison_path = Path(args.comparison_json) if args.comparison_json else output_dir / "kg_quality_comparison.json"
            _write_json(
                comparison_path,
                {
                    "comparison": comparison,
                    "regression_detected": regression,
                    "regression_reasons": reasons,
                },
            )
            print(
                "KG quality comparison: "
                f"baseline={comparison['baseline_quality']:.4f} "
                f"current={comparison['current_quality']:.4f} "
                f"delta={comparison['overall_quality_delta']:+.4f} "
                f"regression={'yes' if regression else 'no'}",
                file=sys.stderr,
            )
            temporal_comparison_line = _build_temporal_comparison_summary(comparison)
            if temporal_comparison_line:
                print(temporal_comparison_line, file=sys.stderr)

        operator_line = _build_operator_summary(report)
        if operator_line:
            print(operator_line, file=sys.stderr)
        print(json.dumps(report, indent=2))
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
