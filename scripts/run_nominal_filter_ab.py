#!/usr/bin/env python3
"""Run ENH-NOM-04 nominal filter A/B benchmark.

Profiles:
1. `legacy`   -> TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS=0
2. `enh_nom4` -> TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS=1

For each profile the script:
- refreshes noun-chunk nominal materialization in Neo4j,
- runs strict MEANTIME batch evaluation with identical scope,
- prints entity-layer deltas and a recommendation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from textgraphx.database.client import make_graph_from_config
from textgraphx.evaluation.meantime_evaluator import (
    _resolve_graph_doc_id,
    parse_meantime_xml,
)
from textgraphx.pipeline.phases.refinement import RefinementPhase


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    strict_nominal_filters: bool


def _base_env(strict_nominal_filters: bool) -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "").strip()
    if not existing:
        env["PYTHONPATH"] = "src"
    elif "src" not in existing.split(":"):
        env["PYTHONPATH"] = f"src:{existing}"
    env["TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS"] = "1" if strict_nominal_filters else "0"
    return env


def _iter_gold_xml_files(gold_dir: Path) -> list[Path]:
    return sorted(path for path in gold_dir.glob("*.xml") if path.is_file())


def _collect_entity_projection_diagnostics(
    *,
    gold_dir: Path,
    discourse_only: bool,
) -> dict[str, int | bool]:
    graph = make_graph_from_config()
    try:
        gold_files = _iter_gold_xml_files(gold_dir)
        gold_docs: list[tuple[str, Any]] = []
        for xml_path in gold_files:
            raw_doc_id = ""
            parsed_doc: Any | None = None
            try:
                parsed_doc = parse_meantime_xml(str(xml_path))
                raw_doc_id = str(parsed_doc.doc_id or "").strip()
            except Exception:
                parsed_doc = None
                raw_doc_id = ""
            if not raw_doc_id:
                raw_doc_id = xml_path.stem
            resolved = _resolve_graph_doc_id(graph, raw_doc_id)
            if resolved is None or parsed_doc is None:
                continue
            gold_docs.append((str(resolved), parsed_doc))

        resolved_doc_ids = sorted({doc_id for doc_id, _ in gold_docs})
        if not resolved_doc_ids:
            return {
                "discourse_only": discourse_only,
                "gold_docs_total": len(gold_files),
                "gold_docs_resolved": 0,
                "projected_mentions_total": 0,
                "projected_mentions_nc": 0,
                "projected_mentions_nc_discourse_prop_true": 0,
                "projected_spans_total": 0,
                "projected_spans_non_nc": 0,
                "projected_spans_nc": 0,
                "projected_spans_nc_exclusive": 0,
                "projected_spans_nc_shared_with_non_nc": 0,
                "projected_spans_nc_exclusive_matching_gold_span": 0,
                "projected_spans_nc_exclusive_not_in_gold_span": 0,
            }

        gold_span_bounds: set[tuple[str, int, int]] = set()

        for resolved_doc_id, gold_doc in gold_docs:
            for gm in getattr(gold_doc, "entity_mentions", set()):
                if not getattr(gm, "span", ()):
                    continue
                span_tuple = tuple(int(tok_idx) for tok_idx in gm.span)
                gold_span_bounds.add((resolved_doc_id, min(span_tuple), max(span_tuple)))

        discourse_clause = "AND m:DiscourseEntity" if discourse_only else ""
        rows = graph.run(
            f"""
            MATCH (a:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
            WHERE toString(a.id) IN $doc_ids
            MATCH (tok)-[:IN_MENTION|PARTICIPATES_IN]->(m)
            WHERE (m:EntityMention OR m:NamedEntity OR m:NominalMention OR m:CorefMention OR m:Entity OR m:Concept)
              AND NOT coalesce(m.stale, false)
              {discourse_clause}
            WITH a, m,
                 min(tok.tok_index_doc) AS start_tok,
                 max(tok.tok_index_doc) AS end_tok,
                  head(collect(tok)) AS head_tok,
                 coalesce(m.mention_source, '') AS mention_source,
                  coalesce(m.is_discourse_entity, false) AS is_discourse_entity_prop,
                  coalesce(m.syntactic_type, m.syntacticType, '') AS syntactic_type
              WITH a, m, start_tok, end_tok, head_tok, mention_source, is_discourse_entity_prop, syntactic_type,
                  coalesce(m.nominalHeadPos, head_tok.pos, '') AS head_pos,
                  coalesce(head_tok.upos, '') AS upos
            RETURN DISTINCT
                 toString(a.id) AS doc_id,
                  elementId(m) AS node_id,
                 start_tok,
                 end_tok,
                 mention_source,
                  is_discourse_entity_prop,
                  syntactic_type,
                  head_pos,
                  upos
            """,
            {"doc_ids": resolved_doc_ids},
        ).data()

        allowed_syntactic_types = {"NAM", "NOM", "PRO", "APP", "PRE.NOM"}
        pron_pos_tags = {"PRP", "PRP$", "WP", "WP$"}
        proper_pos_tags = {"NNP", "NNPS"}
        common_noun_pos_tags = {"NN", "NNS"}

        node_ids: set[str] = set()
        nc_node_ids: set[str] = set()
        spans_total: set[tuple[str, int, int]] = set()
        spans_nc: set[tuple[str, int, int]] = set()
        spans_non_nc: set[tuple[str, int, int]] = set()
        nc_discourse_prop_true = 0

        for row in rows:
            node_id = str(row["node_id"])
            doc_id = str(row["doc_id"])
            start_tok = int(row["start_tok"])
            end_tok = int(row["end_tok"])
            mention_source = str(row.get("mention_source") or "")
            syntactic_type = str(row.get("syntactic_type") or "").strip().upper()
            head_pos = str(row.get("head_pos") or "").strip().upper()
            upos = str(row.get("upos") or "").strip().upper()

            if not syntactic_type:
                if head_pos in pron_pos_tags or upos == "PRON":
                    syntactic_type = "PRO"
                elif head_pos in proper_pos_tags:
                    syntactic_type = "NAM"
                elif head_pos in common_noun_pos_tags:
                    syntactic_type = "NOM"

            if syntactic_type == "NOMINAL":
                syntactic_type = "NOM"

            if syntactic_type not in allowed_syntactic_types:
                continue

            span_key = (doc_id, start_tok, end_tok)

            node_ids.add(node_id)
            spans_total.add(span_key)

            is_nc = mention_source in {"nc", "noun_chunk_nominal"}
            if is_nc:
                nc_node_ids.add(node_id)
                spans_nc.add(span_key)
                if bool(row.get("is_discourse_entity_prop", False)):
                    nc_discourse_prop_true += 1
            else:
                spans_non_nc.add(span_key)

        nc_exclusive_spans = spans_nc - spans_non_nc

        return {
            "discourse_only": discourse_only,
            "gold_docs_total": len(gold_files),
            "gold_docs_resolved": len(resolved_doc_ids),
            "projected_mentions_total": len(node_ids),
            "projected_mentions_nc": len(nc_node_ids),
            "projected_mentions_nc_discourse_prop_true": nc_discourse_prop_true,
            "projected_spans_total": len(spans_total),
            "projected_spans_non_nc": len(spans_non_nc),
            "projected_spans_nc": len(spans_nc),
            "projected_spans_nc_exclusive": len(nc_exclusive_spans),
            "projected_spans_nc_shared_with_non_nc": len(spans_nc & spans_non_nc),
            "projected_spans_nc_exclusive_matching_gold_span": len(nc_exclusive_spans & gold_span_bounds),
            "projected_spans_nc_exclusive_not_in_gold_span": len(nc_exclusive_spans - gold_span_bounds),
        }
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _count_noun_chunk_nominals() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (em:EntityMention:NominalMention)
            WHERE coalesce(em.mention_source, '') IN ['nc', 'noun_chunk_nominal']
            RETURN count(em) AS c
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("c", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _count_noun_chunk_entities() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (e:Entity)
            WHERE coalesce(e.source, '') = 'noun_chunk_nominal'
               OR coalesce(e.provenance_rule_id, '') = 'refinement.materialize_nominal_mentions_from_noun_chunks'
               OR e.source_noun_chunk_id IS NOT NULL
            RETURN count(e) AS c
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("c", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _count_fa_entitymention_links() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (:FrameArgument)-[r:REFERS_TO {provenance_rule_id: 'link_fa_entitymention_entity'}]->(:Entity)
            RETURN count(r) AS c
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("c", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _delete_noun_chunk_nominals() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (em:EntityMention:NominalMention)
            WHERE coalesce(em.mention_source, '') IN ['nc', 'noun_chunk_nominal']
            WITH collect(em) AS ems
            UNWIND ems AS em
            DETACH DELETE em
            RETURN size(ems) AS deleted
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("deleted", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _delete_noun_chunk_entities() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (e:Entity)
            WHERE coalesce(e.source, '') = 'noun_chunk_nominal'
               OR coalesce(e.provenance_rule_id, '') = 'refinement.materialize_nominal_mentions_from_noun_chunks'
               OR e.source_noun_chunk_id IS NOT NULL
            WITH collect(e) AS entities
            UNWIND entities AS e
            DETACH DELETE e
            RETURN size(entities) AS deleted
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("deleted", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _delete_fa_entitymention_links() -> int:
    graph = make_graph_from_config()
    try:
        rows = graph.run(
            """
            MATCH (:FrameArgument)-[r:REFERS_TO {provenance_rule_id: 'link_fa_entitymention_entity'}]->(:Entity)
            WITH collect(r) AS links
            FOREACH (link IN links | DELETE link)
            RETURN size(links) AS deleted
            """
        ).data()
        if not rows:
            return 0
        return int(rows[0].get("deleted", 0) or 0)
    finally:
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            close_fn()


def _refresh_nominal_materialization(strict_nominal_filters: bool) -> dict[str, int | bool]:
    os.environ["TEXTGRAPHX_ENH_NOM_04_STRICT_FILTERS"] = "1" if strict_nominal_filters else "0"

    mentions_before = _count_noun_chunk_nominals()
    entities_before = _count_noun_chunk_entities()
    fa_links_before = _count_fa_entitymention_links()

    mentions_deleted = _delete_noun_chunk_nominals()
    entities_deleted = _delete_noun_chunk_entities()
    fa_links_deleted = _delete_fa_entitymention_links()

    refiner = RefinementPhase(argv=[])
    refiner.run_rule_family("nominal_mentions")
    refiner.run_rule_family("mention_cleanup")

    mentions_after = _count_noun_chunk_nominals()
    entities_after = _count_noun_chunk_entities()
    fa_links_after = _count_fa_entitymention_links()
    return {
        "strict_nominal_filters": strict_nominal_filters,
        "noun_chunk_nominals_before": mentions_before,
        "noun_chunk_nominals_deleted": mentions_deleted,
        "noun_chunk_nominals_after": mentions_after,
        "noun_chunk_entities_before": entities_before,
        "noun_chunk_entities_deleted": entities_deleted,
        "noun_chunk_entities_after": entities_after,
        "fa_entitymention_links_before": fa_links_before,
        "fa_entitymention_links_deleted": fa_links_deleted,
        "fa_entitymention_links_after": fa_links_after,
    }


def _run_profile(
    *,
    repo_root: Path,
    python_bin: str,
    gold_dir: Path,
    output_dir: Path,
    date_tag: str,
    profile: ProfileConfig,
) -> tuple[Path, dict[str, int | bool], dict[str, int | bool]]:
    refresh_stats = _refresh_nominal_materialization(profile.strict_nominal_filters)
    projection_stats = _collect_entity_projection_diagnostics(
        gold_dir=gold_dir,
        discourse_only=True,
    )

    stem = f"eval_report_nominal_filter_{profile.name}_{date_tag}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    csv_prefix = output_dir / stem

    cmd = [
        python_bin,
        "-m",
        "textgraphx.tools.evaluate_meantime",
        "--gold-dir",
        str(gold_dir),
        "--pred-neo4j",
        "--analysis-mode",
        "strict",
        "--discourse-only",
        "--nominal-precision-filters",
        "--nominal-profile-mode",
        "all",
        "--relation-scope",
        "tlink,has_participant",
        "--out-json",
        str(json_path),
        "--out-markdown",
        str(md_path),
        "--export-csv-prefix",
        str(csv_prefix),
    ]

    print(f"[refresh] {profile.name} strict_nominal_filters={int(profile.strict_nominal_filters)}")
    print(
        "  noun_chunk_nominals: "
        f"before={refresh_stats['noun_chunk_nominals_before']} "
        f"deleted={refresh_stats['noun_chunk_nominals_deleted']} "
        f"after={refresh_stats['noun_chunk_nominals_after']}"
    )
    print(
        "  noun_chunk_entities: "
        f"before={refresh_stats['noun_chunk_entities_before']} "
        f"deleted={refresh_stats['noun_chunk_entities_deleted']} "
        f"after={refresh_stats['noun_chunk_entities_after']}"
    )
    print(
        "  fa_refers_to_links(link_fa_entitymention_entity): "
        f"before={refresh_stats['fa_entitymention_links_before']} "
        f"deleted={refresh_stats['fa_entitymention_links_deleted']} "
        f"after={refresh_stats['fa_entitymention_links_after']}"
    )
    print(
        "  entity_projection(discourse_only): "
        f"docs={projection_stats['gold_docs_resolved']} "
        f"mentions={projection_stats['projected_mentions_total']} "
        f"mentions_nc={projection_stats['projected_mentions_nc']} "
        f"spans={projection_stats['projected_spans_total']} "
        f"spans_nc_exclusive={projection_stats['projected_spans_nc_exclusive']} "
        f"spans_nc_exclusive_gold_overlap={projection_stats['projected_spans_nc_exclusive_matching_gold_span']}"
    )
    print(f"[run] {profile.name}")

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=_base_env(profile.strict_nominal_filters),
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout, file=sys.stderr)
        if proc.stderr.strip():
            print(proc.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    return json_path, refresh_stats, projection_stats


def _load_metrics(report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    strict_micro = report["aggregate"]["micro"]["strict"]
    strict_by_kind = report["aggregate"]["relation_by_kind"]["micro"]["strict"]

    return {
        "entity": dict(strict_micro["entity"]),
        "event": dict(strict_micro["event"]),
        "timex": dict(strict_micro["timex"]),
        "relation": dict(strict_micro["relation"]),
        "has_participant": dict(strict_by_kind.get("has_participant", {})),
        "tlink": dict(strict_by_kind.get("tlink", {})),
        "evaluation_scope": report.get("evaluation_scope", {}),
    }


def _delta(after: float | int, before: float | int) -> float | int:
    if isinstance(after, int) and isinstance(before, int):
        return after - before
    return float(after) - float(before)


def _print_summary(metrics: dict[str, dict[str, Any]]) -> None:
    legacy = metrics["legacy"]
    enh = metrics["enh_nom4"]

    print("\n=== Absolute Strict Micro Metrics ===")
    for name in ("legacy", "enh_nom4"):
        m = metrics[name]
        em = m["entity"]
        print(name)
        print(
            "  entity: "
            f"P={em['precision']:.6f} R={em['recall']:.6f} F1={em['f1']:.6f} "
            f"TP={em['tp']} FP={em['fp']} FN={em['fn']}"
        )

    print("\n=== Delta (enh_nom4 - legacy) ===")
    em_l = legacy["entity"]
    em_e = enh["entity"]
    for key in ("precision", "recall", "f1", "tp", "fp", "fn"):
        d = _delta(em_e[key], em_l[key])
        if isinstance(d, int):
            print(f"  entity_{key}: {d:+d}")
        else:
            print(f"  entity_{key}: {d:+.12f}")


def _print_projection_summary(projection: dict[str, dict[str, Any]]) -> None:
    legacy = projection["legacy"]
    enh = projection["enh_nom4"]

    print("\n=== Entity Projection Diagnostics (Evaluator Scope) ===")
    for name in ("legacy", "enh_nom4"):
        p = projection[name]
        print(name)
        print(
            "  projected: "
            f"mentions={p['projected_mentions_total']} "
            f"mentions_nc={p['projected_mentions_nc']} "
            f"spans={p['projected_spans_total']} "
            f"spans_nc={p['projected_spans_nc']} "
            f"spans_nc_exclusive={p['projected_spans_nc_exclusive']} "
            f"spans_nc_shared={p['projected_spans_nc_shared_with_non_nc']}"
        )
        print(
            "  projected_nc_vs_gold: "
            f"exclusive_gold_overlap={p['projected_spans_nc_exclusive_matching_gold_span']} "
            f"exclusive_not_in_gold={p['projected_spans_nc_exclusive_not_in_gold_span']}"
        )

    print("\n=== Projection Delta (enh_nom4 - legacy) ===")
    for key in (
        "projected_mentions_total",
        "projected_mentions_nc",
        "projected_spans_total",
        "projected_spans_nc",
        "projected_spans_nc_exclusive",
        "projected_spans_nc_shared_with_non_nc",
        "projected_spans_nc_exclusive_matching_gold_span",
        "projected_spans_nc_exclusive_not_in_gold_span",
    ):
        d = int(enh[key]) - int(legacy[key])
        print(f"  {key}: {d:+d}")


def _build_root_cause_verdict(
    metrics: dict[str, dict[str, Any]],
    projection: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    legacy_entity = metrics["legacy"]["entity"]
    enh_entity = metrics["enh_nom4"]["entity"]

    strict_entity_delta = {
        "tp": int(enh_entity["tp"]) - int(legacy_entity["tp"]),
        "fp": int(enh_entity["fp"]) - int(legacy_entity["fp"]),
        "fn": int(enh_entity["fn"]) - int(legacy_entity["fn"]),
        "precision": float(enh_entity["precision"]) - float(legacy_entity["precision"]),
        "recall": float(enh_entity["recall"]) - float(legacy_entity["recall"]),
        "f1": float(enh_entity["f1"]) - float(legacy_entity["f1"]),
    }

    legacy_proj = projection["legacy"]
    enh_proj = projection["enh_nom4"]
    projected_nc_vs_gold_delta = {
        "exclusive_total": int(enh_proj["projected_spans_nc_exclusive"])
        - int(legacy_proj["projected_spans_nc_exclusive"]),
        "exclusive_gold_overlap": int(enh_proj["projected_spans_nc_exclusive_matching_gold_span"])
        - int(legacy_proj["projected_spans_nc_exclusive_matching_gold_span"]),
        "exclusive_not_in_gold": int(enh_proj["projected_spans_nc_exclusive_not_in_gold_span"])
        - int(legacy_proj["projected_spans_nc_exclusive_not_in_gold_span"]),
    }

    entity_counts_unchanged = (
        strict_entity_delta["tp"] == 0
        and strict_entity_delta["fp"] == 0
        and strict_entity_delta["fn"] == 0
    )
    removed_nc_exclusive_spans = projected_nc_vs_gold_delta["exclusive_total"] < 0
    removed_only_non_gold_nc_exclusive_spans = (
        projected_nc_vs_gold_delta["exclusive_gold_overlap"] == 0
        and projected_nc_vs_gold_delta["exclusive_not_in_gold"] < 0
    )

    verdict_code = "indeterminate"
    verdict_text = "No strong projection-vs-gold causal pattern was detected."
    if (
        entity_counts_unchanged
        and removed_nc_exclusive_spans
        and removed_only_non_gold_nc_exclusive_spans
    ):
        verdict_code = "strict_removed_non_gold_nc_exclusive_without_entity_impact"
        verdict_text = (
            "Strict filtering removed NC-exclusive projected spans that had no exact gold overlap, "
            "so strict entity TP/FP/FN remained unchanged."
        )

    return {
        "code": verdict_code,
        "text": verdict_text,
        "flags": {
            "entity_counts_unchanged": entity_counts_unchanged,
            "removed_nc_exclusive_spans": removed_nc_exclusive_spans,
            "removed_only_non_gold_nc_exclusive_spans": removed_only_non_gold_nc_exclusive_spans,
        },
        "strict_entity_delta": strict_entity_delta,
        "projected_nc_vs_gold_delta": projected_nc_vs_gold_delta,
    }


def _recommend_profile(metrics: dict[str, dict[str, Any]]) -> str:
    ranking = sorted(
        metrics.items(),
        key=lambda item: (
            float(item[1]["entity"]["f1"]),
            float(item[1]["entity"]["precision"]),
        ),
        reverse=True,
    )
    return ranking[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ENH-NOM-04 A/B benchmark")
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python interpreter to use for evaluator runs.",
    )
    parser.add_argument(
        "--gold-dir",
        default="src/textgraphx/datastore/annotated",
        help="Gold annotation directory used by the evaluator.",
    )
    parser.add_argument(
        "--output-dir",
        default="src/textgraphx/datastore/evaluation/latest",
        help="Directory for generated evaluation artifacts.",
    )
    parser.add_argument(
        "--date-tag",
        default=datetime.now(timezone.utc).strftime("%Y%m%d"),
        help="Suffix tag for generated report filenames.",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional output path for benchmark summary JSON.",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    gold_dir = (repo_root / args.gold_dir).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = [
        ProfileConfig(name="legacy", strict_nominal_filters=False),
        ProfileConfig(name="enh_nom4", strict_nominal_filters=True),
    ]

    report_paths: dict[str, Path] = {}
    refresh_stats_by_profile: dict[str, dict[str, int | bool]] = {}
    projection_by_profile: dict[str, dict[str, int | bool]] = {}
    for profile in profiles:
        report_path, refresh_stats, projection_stats = _run_profile(
            repo_root=repo_root,
            python_bin=args.python_bin,
            gold_dir=gold_dir,
            output_dir=output_dir,
            date_tag=args.date_tag,
            profile=profile,
        )
        report_paths[profile.name] = report_path
        refresh_stats_by_profile[profile.name] = refresh_stats
        projection_by_profile[profile.name] = projection_stats

    metrics = {name: _load_metrics(path) for name, path in report_paths.items()}
    _print_summary(metrics)
    _print_projection_summary(projection_by_profile)

    verdict = _build_root_cause_verdict(metrics, projection_by_profile)
    print("\n=== Diagnostic Verdict ===")
    print(f"code: {verdict['code']}")
    print(f"text: {verdict['text']}")

    recommendation = _recommend_profile(metrics)
    print("\n=== Recommendation ===")
    print(f"recommended_profile: {recommendation}")

    summary_payload = {
        "date_tag": args.date_tag,
        "report_paths": {k: str(v) for k, v in report_paths.items()},
        "refresh_stats": refresh_stats_by_profile,
        "projection_diagnostics": projection_by_profile,
        "diagnostic_verdict": verdict,
        "metrics": metrics,
        "recommended_profile": recommendation,
    }

    summary_json_path = (
        Path(args.summary_json).resolve()
        if args.summary_json
        else output_dir / f"nominal_filter_ab_summary_{args.date_tag}.json"
    )
    summary_json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    print(f"summary_json: {summary_json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
