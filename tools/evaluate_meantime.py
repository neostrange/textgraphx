"""CLI for MEANTIME-oriented evaluation.

Examples:
  python -m textgraphx.tools.evaluate_meantime \
    --gold textgraphx/datastore/annotated/76437_Markets_dragged_down_by_credit_crisis.xml \
    --pred-xml textgraphx/datastore/annotated/76437_Markets_dragged_down_by_credit_crisis.xml

  python -m textgraphx.tools.evaluate_meantime \
    --gold textgraphx/datastore/annotated/76437_Markets_dragged_down_by_credit_crisis.xml \
    --pred-neo4j --doc-id 76437
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from textgraphx.evaluation.meantime_evaluator import (
    EvaluationMapping,
    aggregate_reports,
    build_dual_scorecards_from_aggregate,
    build_dual_scorecards_from_report,
    build_document_from_neo4j,
    build_dataset_diagnostics,
    build_document_diagnostics,
    check_projection_determinism,
    evaluate_documents,
    flatten_aggregate_rows_for_csv,
    flatten_report_rows_for_csv,
    parse_meantime_xml,
    render_markdown_report,
)


def _default_output_paths() -> tuple[Path, Path, Path]:
    base_dir = Path(__file__).resolve().parents[1] / "datastore" / "evaluation"
    return base_dir / "eval_report.json", base_dir / "eval_report.md", base_dir / "eval_report"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate pipeline output against MEANTIME-style gold")
    parser.add_argument("--gold", help="Path to one MEANTIME-style gold XML")
    parser.add_argument("--gold-dir", help="Path to directory of MEANTIME-style gold XML files")
    parser.add_argument("--pred-xml", help="Path to predicted XML in compatible format")
    parser.add_argument("--pred-xml-dir", help="Path to directory of predicted XML files (matched by filename)")
    parser.add_argument(
        "--pred-neo4j",
        action="store_true",
        help="Use Neo4j as prediction source instead of --pred-xml",
    )
    parser.add_argument("--doc-id", help="Document id for graph extraction (required with --pred-neo4j)")
    parser.add_argument("--mapping-config", help="Optional JSON mapping config for attribute matching")
    parser.add_argument("--analysis-mode", choices=["strict", "relaxed"], default="strict", help="Mode used for diagnostics and suggestion generation")
    parser.add_argument("--f1-threshold", type=float, default=0.75, help="Threshold for weak-layer and hotspot detection")
    parser.add_argument("--max-examples", type=int, default=5, help="Maximum failure examples per bucket")
    parser.add_argument(
        "--out-json",
        help="Optional path to write full JSON report (defaults to textgraphx/datastore/evaluation/eval_report.json)",
    )
    parser.add_argument(
        "--out-markdown",
        help="Optional path to write markdown executive report (defaults to textgraphx/datastore/evaluation/eval_report.md)",
    )
    parser.add_argument(
        "--export-csv-prefix",
        help="Optional prefix for CSV export files (<prefix>_docs.csv and <prefix>_summary.csv); defaults to textgraphx/datastore/evaluation/eval_report",
    )
    parser.add_argument("--overlap-threshold", type=float, default=0.5, help="Relaxed matching IoU threshold")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument(
        "--discourse-only",
        action="store_true",
        default=False,
        help=(
            "Restrict predicted entities to discourse-relevant mentions only. "
            "Entities must carry the :DiscourseEntity label (stamped by RefinementPhase "
            "rule tag_discourse_relevant_entities). Event projection is left unchanged. "
            "Produces a filtered view comparable to MEANTIME "
            "annotation scope without modifying the evaluation gold."
        ),
    )
    parser.add_argument(
        "--normalize-nominal-boundaries",
        dest="normalize_nominal_boundaries",
        action="store_true",
        default=True,
        help="Trim leading determiners and trailing punctuation for nominal mentions during Neo4j projection.",
    )
    parser.add_argument(
        "--no-normalize-nominal-boundaries",
        dest="normalize_nominal_boundaries",
        action="store_false",
        help="Disable nominal boundary normalization during Neo4j projection.",
    )
    parser.add_argument(
        "--gold-like-nominal-filter",
        action="store_true",
        default=False,
        help=(
            "Apply evaluator-side nominal projection filtering to better mirror gold scope "
            "(eventive-noun drop, proper-name reclassification, salience gate)."
        ),
    )
    parser.add_argument(
        "--nominal-profile-mode",
        choices=["all", "eventive", "salient", "candidate-gold", "background"],
        default="all",
        help=(
            "Evaluator-side nominal profile projection mode for Neo4j predictions. "
            "Applies only to nominal entity mentions and leaves non-nominal entities unchanged."
        ),
    )
    return parser


def _build_operator_summary(report: dict) -> str | None:
    """Build concise operator summary without affecting JSON stdout payload."""
    if report.get("mode") != "batch":
        return None

    evaluated = int(report.get("documents_evaluated", 0))
    skipped = report.get("skipped_prediction_files") or []
    return f"Batch evaluation summary: evaluated={evaluated}, skipped_missing_predictions={len(skipped)}"


def _write_csv_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _load_mapping(path: str | None) -> EvaluationMapping:
    if not path:
        return EvaluationMapping()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    mention_attr_keys = {
        str(k): tuple(str(x) for x in v)
        for k, v in dict(raw.get("mention_attr_keys", {})).items()
    }
    relation_attr_keys = {
        str(k): tuple(str(x) for x in v)
        for k, v in dict(raw.get("relation_attr_keys", {})).items()
    }
    return EvaluationMapping(
        mention_attr_keys=mention_attr_keys or EvaluationMapping().mention_attr_keys,
        relation_attr_keys=relation_attr_keys or EvaluationMapping().relation_attr_keys,
    )


def _evaluate_single(args: argparse.Namespace, mapping: EvaluationMapping) -> dict:
    gold_doc = parse_meantime_xml(args.gold)

    if args.pred_xml:
        predicted_doc = parse_meantime_xml(args.pred_xml)
        projection_determinism = None
    else:
        if args.doc_id is None:
            raise ValueError("--doc-id is required when using --pred-neo4j")
        from textgraphx.neo4j_client import make_graph_from_config

        graph = make_graph_from_config()
        try:
            predicted_doc = build_document_from_neo4j(
                graph=graph,
                doc_id=args.doc_id,
                gold_token_sequence=gold_doc.token_sequence,
                discourse_only=getattr(args, "discourse_only", False),
                    normalize_nominal_boundaries=getattr(args, "normalize_nominal_boundaries", True),
                    gold_like_nominal_filter=getattr(args, "gold_like_nominal_filter", False),
                    nominal_profile_mode=getattr(args, "nominal_profile_mode", "all"),
            )
            projection_determinism = check_projection_determinism(
                graph=graph,
                doc_id=args.doc_id,
                runs=int(getattr(args, "projection_determinism_runs", 2)),
                gold_token_sequence=gold_doc.token_sequence,
                discourse_only=getattr(args, "discourse_only", False),
                normalize_nominal_boundaries=getattr(args, "normalize_nominal_boundaries", True),
                gold_like_nominal_filter=getattr(args, "gold_like_nominal_filter", False),
                nominal_profile_mode=getattr(args, "nominal_profile_mode", "all"),
            )
        finally:
            if hasattr(graph, "close"):
                graph.close()

    base = evaluate_documents(
        gold_doc=gold_doc,
        predicted_doc=predicted_doc,
        overlap_threshold=float(args.overlap_threshold),
        mapping=mapping,
        max_examples=max(1, int(args.max_examples)),
    )
    base["diagnostics"] = build_document_diagnostics(
        base,
        mode=args.analysis_mode,
        f1_threshold=float(args.f1_threshold),
    )
    base["scorecards"] = build_dual_scorecards_from_report(base)
    if projection_determinism is not None:
        base["projection_determinism"] = projection_determinism
    base["evaluation_scope"] = {
        "discourse_only": bool(getattr(args, "discourse_only", False)),
        "entity_filter": "DiscourseEntity label" if getattr(args, "discourse_only", False) else "none",
        "event_filter": "none",
        "nominal_profile_mode": str(getattr(args, "nominal_profile_mode", "all")),
        "gold_like_nominal_filter": bool(getattr(args, "gold_like_nominal_filter", False)),
    }
    return base


def _evaluate_batch(args: argparse.Namespace, mapping: EvaluationMapping) -> dict:
    gold_dir = Path(args.gold_dir)
    gold_files = sorted(gold_dir.glob("*.xml"))
    if not gold_files:
        raise ValueError(f"No gold XML files found in: {gold_dir}")

    reports = []
    skipped_prediction_files: list[str] = []
    graph = None
    if args.pred_neo4j:
        from textgraphx.neo4j_client import make_graph_from_config

        graph = make_graph_from_config()
    try:
        for gold_path in gold_files:
            gold_doc = parse_meantime_xml(str(gold_path))
            if args.pred_xml_dir:
                pred_path = Path(args.pred_xml_dir) / gold_path.name
                if not pred_path.exists():
                    skipped_prediction_files.append(gold_path.name)
                    continue
                predicted_doc = parse_meantime_xml(str(pred_path))
            else:
                predicted_doc = build_document_from_neo4j(
                    graph=graph,
                    doc_id=gold_doc.doc_id,
                    gold_token_sequence=gold_doc.token_sequence,
                    discourse_only=getattr(args, "discourse_only", False),
                    normalize_nominal_boundaries=getattr(args, "normalize_nominal_boundaries", True),
                    gold_like_nominal_filter=getattr(args, "gold_like_nominal_filter", False),
                    nominal_profile_mode=getattr(args, "nominal_profile_mode", "all"),
                )

            reports.append(
                evaluate_documents(
                    gold_doc=gold_doc,
                    predicted_doc=predicted_doc,
                    overlap_threshold=float(args.overlap_threshold),
                    mapping=mapping,
                    max_examples=max(1, int(args.max_examples)),
                )
            )
    finally:
        if graph is not None and hasattr(graph, "close"):
            graph.close()

    aggregate = aggregate_reports(reports)
    diagnostics = build_dataset_diagnostics(
        reports,
        aggregate,
        mode=args.analysis_mode,
        f1_threshold=float(args.f1_threshold),
    )
    scorecards = build_dual_scorecards_from_aggregate(aggregate)
    return {
        "mode": "batch",
        "documents_evaluated": len(reports),
        "skipped_prediction_files": skipped_prediction_files,
        "evaluation_scope": {
            "discourse_only": bool(getattr(args, "discourse_only", False)),
            "entity_filter": "DiscourseEntity label" if getattr(args, "discourse_only", False) else "none",
            "event_filter": "none",
            "nominal_profile_mode": str(getattr(args, "nominal_profile_mode", "all")),
            "gold_like_nominal_filter": bool(getattr(args, "gold_like_nominal_filter", False)),
        },
        "aggregate": aggregate,
        "scorecards": scorecards,
        "diagnostics": diagnostics,
        "reports": reports,
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    mapping = _load_mapping(args.mapping_config)

    single_mode = bool(args.gold)
    batch_mode = bool(args.gold_dir)
    if single_mode == batch_mode:
        parser.error("Provide exactly one gold input mode: --gold OR --gold-dir")

    if batch_mode and bool(args.pred_xml_dir) == bool(args.pred_neo4j):
        parser.error("For --gold-dir, provide exactly one prediction source: --pred-xml-dir OR --pred-neo4j")

    if single_mode and bool(args.pred_xml) == bool(args.pred_neo4j):
        parser.error("For --gold, provide exactly one prediction source: --pred-xml OR --pred-neo4j")

    if batch_mode:
        report = _evaluate_batch(args, mapping)
    else:
        try:
            report = _evaluate_single(args, mapping)
        except ValueError as e:
            parser.error(str(e))

    default_json, default_md, default_prefix = _default_output_paths()
    out_json = Path(args.out_json) if args.out_json else default_json
    out_md = Path(args.out_markdown) if args.out_markdown else default_md
    prefix = Path(args.export_csv_prefix) if args.export_csv_prefix else default_prefix

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(report))

    if prefix:
        if report.get("mode") == "batch":
            doc_rows = flatten_report_rows_for_csv(report.get("reports", []), mode=args.analysis_mode)
            summary_rows = flatten_aggregate_rows_for_csv(report.get("aggregate", {}))
        else:
            doc_rows = flatten_report_rows_for_csv([report], mode=args.analysis_mode)
            summary_rows = flatten_aggregate_rows_for_csv(
                {
                    "micro": {
                        args.analysis_mode: {
                            layer: report.get(args.analysis_mode, {}).get(layer, {})
                            for layer in ("entity", "event", "timex", "relation")
                        }
                    },
                    "macro": {
                        args.analysis_mode: {
                            layer: {
                                "precision": float(report.get(args.analysis_mode, {}).get(layer, {}).get("precision", 0.0)),
                                "recall": float(report.get(args.analysis_mode, {}).get(layer, {}).get("recall", 0.0)),
                                "f1": float(report.get(args.analysis_mode, {}).get(layer, {}).get("f1", 0.0)),
                            }
                            for layer in ("entity", "event", "timex", "relation")
                        }
                    },
                }
            )
        _write_csv_rows(Path(f"{prefix}_docs.csv"), doc_rows)
        _write_csv_rows(Path(f"{prefix}_summary.csv"), summary_rows)

    summary_line = _build_operator_summary(report)
    if summary_line:
        print(summary_line, file=sys.stderr)

    if args.pretty:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
