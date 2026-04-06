"""CLI for KG quality evaluation using the unified full-stack harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


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

    from textgraphx.config import get_config
    from textgraphx.neo4j_client import make_graph_from_config
    from textgraphx.evaluation.fullstack_harness import FullStackEvaluator

    cfg = get_config()
    config_dict = _config_to_hashable_dict(cfg)

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

        export_json, export_csv, export_md = _ensure_any_export_requested(args)
        if export_json:
            evaluator.export_json(suite, output_dir / "kg_quality_report.json")
        if export_csv:
            evaluator.export_csv(suite, output_dir / "kg_quality_scores.csv")
        if export_md:
            evaluator.export_markdown(suite, output_dir / "kg_quality_report.md")

        summary = {
            "overall_quality": suite.overall_quality(),
            "quality_tier": _quality_tier(suite.overall_quality()),
            "conclusive": suite.conclusiveness()[0],
            "reasons": suite.conclusiveness()[1],
            "documents": len(dataset_paths),
        }
        diagnostics = suite.runtime_diagnostics or {}
        totals = diagnostics.get("totals", {}) if isinstance(diagnostics, dict) else {}
        if totals:
            summary["entity_state_coverage_ratio"] = totals.get("entity_state_coverage_ratio", 0.0)
            summary["entity_mentions_with_state_count"] = totals.get("entity_mentions_with_state_count", 0)
            summary["entity_specificity_coverage_ratio"] = totals.get("entity_specificity_coverage_ratio", 0.0)
            summary["mentions_with_ent_class_count"] = totals.get("mentions_with_ent_class_count", 0)
            summary["event_external_ref_coverage_ratio"] = totals.get("event_external_ref_coverage_ratio", 0.0)
            summary["event_nodes_with_external_ref_count"] = totals.get("event_nodes_with_external_ref_count", 0)
            summary["glink_count"] = totals.get("glink_count", 0)
        print(json.dumps(summary, indent=2))
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
