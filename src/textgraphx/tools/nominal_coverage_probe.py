"""Nominal extraction coverage probe.

This utility reports nominal entity/mention coverage and, optionally, runs
refinement to show before/after deltas.

Examples:
  python -m textgraphx.tools.nominal_coverage_probe
  python -m textgraphx.tools.nominal_coverage_probe --doc-id 76437
  python -m textgraphx.tools.nominal_coverage_probe --run-refinement --rule-family nominal_mentions
"""

from __future__ import annotations

import argparse
import json
from typing import Any


def _single_count(graph: Any, query: str, params: dict[str, Any]) -> int:
    rows = graph.run(query, params).data()
    if not rows:
        return 0
    return int(rows[0].get("count", 0))


def _group_counts(graph: Any, query: str, params: dict[str, Any]) -> dict[str, int]:
    rows = graph.run(query, params).data()
    out: dict[str, int] = {}
    for row in rows:
        key = str(row.get("key") or "unknown")
        out[key] = int(row.get("count", 0))
    return out


def _snapshot(graph: Any, doc_id: str | None) -> dict[str, Any]:
    scope_ne = "" if doc_id is None else " AND EXISTS { MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(ne) WHERE toString(d.id) = $doc_id }"
    scope_e = "" if doc_id is None else " AND EXISTS { MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(e) WHERE toString(d.id) = $doc_id }"
    scope_em = "" if doc_id is None else " AND EXISTS { MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(em) WHERE toString(d.id) = $doc_id }"
    scope_fa = "" if doc_id is None else " AND EXISTS { MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(fa) WHERE toString(d.id) = $doc_id }"
    params = {"doc_id": doc_id}

    queries = {
        "named_entities_nominal": f"""
            MATCH (ne:NamedEntity)
            WHERE coalesce(ne.syntacticType, ne.syntactic_type) = 'NOMINAL'{scope_ne}
            RETURN count(DISTINCT ne) AS count
        """,
        "entities_nominal": f"""
            MATCH (e:Entity)
            WHERE coalesce(e.syntacticType, e.type) = 'NOMINAL'{scope_e}
            RETURN count(DISTINCT e) AS count
        """,
        "entity_mentions_nominal": f"""
            MATCH (em:EntityMention)
            WHERE coalesce(em.syntacticType, em.syntactic_type) = 'NOMINAL'{scope_em}
            RETURN count(DISTINCT em) AS count
        """,
        "nominal_mentions_label": f"""
            MATCH (em:EntityMention:NominalMention)
            WHERE 1=1{scope_em}
            RETURN count(DISTINCT em) AS count
        """,
        "frame_args_nominal": f"""
            MATCH (fa:FrameArgument)
            WHERE coalesce(fa.syntacticType, fa.syntactic_type) = 'NOMINAL'{scope_fa}
            RETURN count(DISTINCT fa) AS count
        """,
    }

    source_breakdown = _group_counts(
        graph,
        f"""
        MATCH (em:EntityMention:NominalMention)
        WHERE 1=1{scope_em}
        RETURN coalesce(em.mention_source, 'unknown') AS key, count(DISTINCT em) AS count
        ORDER BY count DESC
        """,
        params,
    )

    entity_source_breakdown = _group_counts(
        graph,
        f"""
        MATCH (e:Entity)
        WHERE coalesce(e.syntacticType, e.type) = 'NOMINAL'{scope_e}
        RETURN coalesce(e.source, 'unknown') AS key, count(DISTINCT e) AS count
        ORDER BY count DESC
        """,
        params,
    )

    entity_subtype_breakdown = _group_counts(
        graph,
        f"""
        MATCH (e:Entity)
        WHERE coalesce(e.syntacticType, e.type) = 'NOMINAL'{scope_e}
        RETURN coalesce(e.nominalSubtype, 'UNSPECIFIED') AS key, count(DISTINCT e) AS count
        ORDER BY count DESC
        """,
        params,
    )

    quantified_subtype_breakdown = _group_counts(
        graph,
        f"""
        MATCH (e:Entity)
        WHERE coalesce(e.syntacticType, e.type) = 'NOMINAL'
                    AND coalesce(e.source, '') = 'quantified_frame_argument'{scope_e}
        RETURN coalesce(e.nominalSubtype, 'UNSPECIFIED') AS key, count(DISTINCT e) AS count
        ORDER BY count DESC
        """,
        params,
    )

    summary = {k: _single_count(graph, q, params) for k, q in queries.items()}
    summary["nominal_mentions_by_source"] = source_breakdown
    summary["nominal_entities_by_source"] = entity_source_breakdown
    summary["nominal_entities_by_subtype"] = entity_subtype_breakdown
    summary["quantified_nominal_entities_by_subtype"] = quantified_subtype_breakdown
    return summary


def _compute_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    for key, before_val in before.items():
        after_val = after.get(key)
        if isinstance(before_val, int) and isinstance(after_val, int):
            delta[key] = after_val - before_val
        elif isinstance(before_val, dict) and isinstance(after_val, dict):
            group_delta: dict[str, int] = {}
            keys = set(before_val.keys()) | set(after_val.keys())
            for k in sorted(keys):
                group_delta[k] = int(after_val.get(k, 0)) - int(before_val.get(k, 0))
            delta[key] = group_delta
    return delta


def _run_refinement(rule_family: str | None) -> None:
    from textgraphx.RefinementPhase import RefinementPhase

    rp = RefinementPhase(argv=[])
    try:
        if rule_family:
            rp.run_rule_family(rule_family)
        else:
            rp.run_all_rule_families()
    finally:
        if hasattr(rp.graph, "close"):
            rp.graph.close()


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Probe nominal extraction coverage")
    p.add_argument("--doc-id", help="Optional document id scope")
    p.add_argument(
        "--run-refinement",
        action="store_true",
        help="Run refinement between before/after snapshots",
    )
    p.add_argument(
        "--rule-family",
        default="nominal_mentions",
        help="Rule family to run when --run-refinement is set. Use 'all' for full refinement.",
    )
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return p


def main() -> int:
    args = _parser().parse_args()

    from textgraphx.database.client import make_graph_from_config

    graph = make_graph_from_config()
    try:
        before = _snapshot(graph, args.doc_id)
    finally:
        if hasattr(graph, "close"):
            graph.close()

    after = None
    delta = None
    ran = False

    if args.run_refinement:
        ran = True
        family = None if (args.rule_family or "").strip().lower() == "all" else args.rule_family
        _run_refinement(family)

        graph2 = make_graph_from_config()
        try:
            after = _snapshot(graph2, args.doc_id)
        finally:
            if hasattr(graph2, "close"):
                graph2.close()
        delta = _compute_delta(before, after)

    payload = {
        "doc_id": args.doc_id,
        "ran_refinement": ran,
        "rule_family": args.rule_family if ran else None,
        "before": before,
        "after": after,
        "delta": delta,
    }

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
