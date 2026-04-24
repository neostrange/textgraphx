"""Cleanup helper for stale NamedEntity nodes.

This script supports dry-run inventory and apply mode for stale NamedEntity
cleanup introduced by incremental re-extraction reconciliation.

Modes:
- dry-run (default): report candidate stale nodes and attached edge counts.
- apply: retire stale mention/canonical edges in batches.
- apply + --detach-delete: additionally detach-delete stale nodes in batches.

Examples:
  python -m textgraphx.tools.cleanup_stale_named_entities --dry-run
  python -m textgraphx.tools.cleanup_stale_named_entities --apply
  python -m textgraphx.tools.cleanup_stale_named_entities --apply --older-than-ms 604800000
  python -m textgraphx.tools.cleanup_stale_named_entities --apply --detach-delete --document-id 42
"""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Optional, Tuple

from textgraphx.database import client as neo4j_client

logger = logging.getLogger(__name__)


def build_scope_filters(
    document_id: Optional[str] = None,
    stale_run_id: Optional[str] = None,
    older_than_ms: Optional[int] = None,
) -> Tuple[str, Dict[str, object]]:
    """Build reusable Cypher scope filters for stale NamedEntity cleanup."""
    where = ["ne.stale = true"]
    params: Dict[str, object] = {}

    if document_id is not None:
        params["doc_prefix"] = f"{document_id}_"
        where.append("coalesce(ne.token_id, ne.id) STARTS WITH $doc_prefix")

    if stale_run_id:
        params["stale_run_id"] = stale_run_id
        where.append("ne.stale_run_id = $stale_run_id")

    if older_than_ms is not None:
        params["older_than_ms"] = int(older_than_ms)
        where.append("ne.stale_at IS NOT NULL")
        where.append("ne.stale_at <= timestamp() - $older_than_ms")

    return " AND ".join(where), params


def _count_stale_nodes(graph, where: str, params: Dict[str, object]) -> int:
    query = f"""
        MATCH (ne:NamedEntity)
        WHERE {where}
        RETURN count(ne) AS cnt
    """
    rows = graph.run(query, params).data()
    return int(rows[0]["cnt"]) if rows else 0


def _count_stale_mention_edges(graph, where: str, params: Dict[str, object]) -> int:
    query = f"""
        MATCH (:TagOccurrence)-[r:IN_MENTION|PARTICIPATES_IN]->(ne:NamedEntity)
        WHERE {where}
        RETURN count(r) AS cnt
    """
    rows = graph.run(query, params).data()
    return int(rows[0]["cnt"]) if rows else 0


def _count_stale_refers_to_edges(graph, where: str, params: Dict[str, object]) -> int:
    query = f"""
        MATCH (ne:NamedEntity)-[r:REFERS_TO]->(:Entity)
        WHERE {where}
        RETURN count(r) AS cnt
    """
    rows = graph.run(query, params).data()
    return int(rows[0]["cnt"]) if rows else 0


def _delete_mention_edges_batch(graph, where: str, params: Dict[str, object], batch_size: int) -> int:
    query = f"""
        MATCH (:TagOccurrence)-[r:IN_MENTION|PARTICIPATES_IN]->(ne:NamedEntity)
        WHERE {where}
        WITH r LIMIT $batch
        DELETE r
        RETURN count(r) AS deleted
    """
    rows = graph.run(query, {**params, "batch": batch_size}).data()
    return int(rows[0]["deleted"]) if rows else 0


def _delete_refers_to_edges_batch(graph, where: str, params: Dict[str, object], batch_size: int) -> int:
    query = f"""
        MATCH (ne:NamedEntity)-[r:REFERS_TO]->(:Entity)
        WHERE {where}
        WITH r LIMIT $batch
        DELETE r
        RETURN count(r) AS deleted
    """
    rows = graph.run(query, {**params, "batch": batch_size}).data()
    return int(rows[0]["deleted"]) if rows else 0


def _detach_delete_stale_nodes_batch(graph, where: str, params: Dict[str, object], batch_size: int) -> int:
    query = f"""
        MATCH (ne:NamedEntity)
        WHERE {where}
        WITH ne LIMIT $batch
        DETACH DELETE ne
        RETURN count(ne) AS deleted
    """
    rows = graph.run(query, {**params, "batch": batch_size}).data()
    return int(rows[0]["deleted"]) if rows else 0


def _delete_in_batches(batch_fn, max_iterations: int) -> int:
    total = 0
    for _ in range(max_iterations):
        deleted = batch_fn()
        total += deleted
        if deleted == 0:
            break
    return total


def run_cleanup(
    graph,
    apply: bool,
    detach_delete: bool,
    batch_size: int,
    max_iterations: int,
    document_id: Optional[str] = None,
    stale_run_id: Optional[str] = None,
    older_than_ms: Optional[int] = None,
) -> Dict[str, int]:
    where, params = build_scope_filters(
        document_id=document_id,
        stale_run_id=stale_run_id,
        older_than_ms=older_than_ms,
    )

    stale_nodes_before = _count_stale_nodes(graph, where, params)
    mention_edges_before = _count_stale_mention_edges(graph, where, params)
    refers_to_edges_before = _count_stale_refers_to_edges(graph, where, params)

    results = {
        "stale_nodes_before": stale_nodes_before,
        "mention_edges_before": mention_edges_before,
        "refers_to_edges_before": refers_to_edges_before,
        "retired_mention_edges": 0,
        "retired_refers_to_edges": 0,
        "deleted_stale_nodes": 0,
        "stale_nodes_after": stale_nodes_before,
        "mention_edges_after": mention_edges_before,
        "refers_to_edges_after": refers_to_edges_before,
    }

    if apply:
        results["retired_mention_edges"] = _delete_in_batches(
            lambda: _delete_mention_edges_batch(graph, where, params, batch_size),
            max_iterations=max_iterations,
        )
        results["retired_refers_to_edges"] = _delete_in_batches(
            lambda: _delete_refers_to_edges_batch(graph, where, params, batch_size),
            max_iterations=max_iterations,
        )
        if detach_delete:
            results["deleted_stale_nodes"] = _delete_in_batches(
                lambda: _detach_delete_stale_nodes_batch(graph, where, params, batch_size),
                max_iterations=max_iterations,
            )

    results["stale_nodes_after"] = _count_stale_nodes(graph, where, params)
    results["mention_edges_after"] = _count_stale_mention_edges(graph, where, params)
    results["refers_to_edges_after"] = _count_stale_refers_to_edges(graph, where, params)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup stale NamedEntity nodes and stale edges")
    parser.add_argument("--dry-run", action="store_true", help="Report counts only; do not write")
    parser.add_argument("--apply", action="store_true", help="Apply edge retirement and optional node delete")
    parser.add_argument("--detach-delete", action="store_true", help="Delete stale NamedEntity nodes with DETACH DELETE")
    parser.add_argument("--document-id", help="Restrict cleanup to one document id prefix")
    parser.add_argument("--stale-run-id", help="Restrict cleanup to a specific stale_run_id")
    parser.add_argument("--older-than-ms", type=int, help="Restrict to nodes stale for at least this many milliseconds")
    parser.add_argument("--batch", type=int, default=5000, help="Batch size for iterative deletes")
    parser.add_argument("--max-iterations", type=int, default=2000, help="Iteration cap per batch delete query")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.dry_run and args.apply:
        raise SystemExit("Use either --dry-run or --apply, not both")
    if args.detach_delete and not args.apply:
        raise SystemExit("--detach-delete requires --apply")
    if args.older_than_ms is not None and args.older_than_ms < 0:
        raise SystemExit("--older-than-ms must be >= 0")

    graph = neo4j_client.make_graph_from_config()
    apply = bool(args.apply)

    results = run_cleanup(
        graph=graph,
        apply=apply,
        detach_delete=bool(args.detach_delete),
        batch_size=args.batch,
        max_iterations=args.max_iterations,
        document_id=args.document_id,
        stale_run_id=args.stale_run_id,
        older_than_ms=args.older_than_ms,
    )

    mode = "apply" if apply else "dry-run"
    logger.info("Stale NamedEntity cleanup (%s)", mode)
    for key in sorted(results.keys()):
        logger.info("%s=%s", key, results[key])


if __name__ == "__main__":
    main()
