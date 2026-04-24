"""Migration helper: backfill participation edge aliases.

Backfills the newer explicit edge types from legacy PARTICIPATES_IN edges:
- IN_FRAME   for TagOccurrence -> (Frame|FrameArgument)
- IN_MENTION for TagOccurrence -> (NamedEntity|EntityMention|CorefMention|Antecedent)

Usage:
  python -m textgraphx.tools.migrate_participation_edges --dry-run
  python -m textgraphx.tools.migrate_participation_edges --apply
"""
from __future__ import annotations

import argparse
import logging
from typing import Dict

from textgraphx.database import client as neo4j_client

logger = logging.getLogger(__name__)


def _count_frame_candidates(graph) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE n:Frame OR n:FrameArgument
        RETURN count(*) AS cnt
    """
    data = graph.run(query).data()
    return int(data[0]["cnt"]) if data else 0


def _count_frame_missing(graph) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE (n:Frame OR n:FrameArgument)
          AND NOT (tok)-[:IN_FRAME]->(n)
        RETURN count(*) AS cnt
    """
    data = graph.run(query).data()
    return int(data[0]["cnt"]) if data else 0


def _count_mention_candidates(graph) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE n:NamedEntity OR n:EntityMention OR n:CorefMention OR n:Antecedent
        RETURN count(*) AS cnt
    """
    data = graph.run(query).data()
    return int(data[0]["cnt"]) if data else 0


def _count_mention_missing(graph) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE (n:NamedEntity OR n:EntityMention OR n:CorefMention OR n:Antecedent)
          AND NOT (tok)-[:IN_MENTION]->(n)
        RETURN count(*) AS cnt
    """
    data = graph.run(query).data()
    return int(data[0]["cnt"]) if data else 0


def _backfill_in_frame_batch(graph, batch_size: int) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE (n:Frame OR n:FrameArgument)
          AND NOT (tok)-[:IN_FRAME]->(n)
        WITH tok, n LIMIT $batch
        MERGE (tok)-[:IN_FRAME]->(n)
        RETURN count(*) AS created
    """
    data = graph.run(query, {"batch": batch_size}).data()
    return int(data[0]["created"]) if data else 0


def _backfill_in_mention_batch(graph, batch_size: int) -> int:
    query = """
        MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
        WHERE (n:NamedEntity OR n:EntityMention OR n:CorefMention OR n:Antecedent)
          AND NOT (tok)-[:IN_MENTION]->(n)
        WITH tok, n LIMIT $batch
        MERGE (tok)-[:IN_MENTION]->(n)
        RETURN count(*) AS created
    """
    data = graph.run(query, {"batch": batch_size}).data()
    return int(data[0]["created"]) if data else 0


def backfill_in_frame(graph, batch_size: int = 5000, max_iterations: int = 2000) -> int:
    total = 0
    for _ in range(max_iterations):
        created = _backfill_in_frame_batch(graph, batch_size)
        total += created
        if created == 0:
            break
    return total


def backfill_in_mention(graph, batch_size: int = 5000, max_iterations: int = 2000) -> int:
    total = 0
    for _ in range(max_iterations):
        created = _backfill_in_mention_batch(graph, batch_size)
        total += created
        if created == 0:
            break
    return total


def run_migration(graph, apply: bool, batch_size: int) -> Dict[str, int]:
    frame_candidates = _count_frame_candidates(graph)
    mention_candidates = _count_mention_candidates(graph)
    frame_missing_before = _count_frame_missing(graph)
    mention_missing_before = _count_mention_missing(graph)

    results = {
        "frame_candidates": frame_candidates,
        "mention_candidates": mention_candidates,
        "frame_missing_before": frame_missing_before,
        "mention_missing_before": mention_missing_before,
        "created_in_frame": 0,
        "created_in_mention": 0,
        "frame_missing_after": frame_missing_before,
        "mention_missing_after": mention_missing_before,
    }

    if apply:
        results["created_in_frame"] = backfill_in_frame(graph, batch_size=batch_size)
        results["created_in_mention"] = backfill_in_mention(graph, batch_size=batch_size)

    results["frame_missing_after"] = _count_frame_missing(graph)
    results["mention_missing_after"] = _count_mention_missing(graph)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill IN_FRAME / IN_MENTION from PARTICIPATES_IN")
    parser.add_argument("--dry-run", action="store_true", help="Compute counts only; do not write")
    parser.add_argument("--apply", action="store_true", help="Apply backfill writes")
    parser.add_argument("--batch", type=int, default=5000, help="Batch size for iterative MERGE")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.dry_run and args.apply:
        raise SystemExit("Use either --dry-run or --apply, not both")

    graph = neo4j_client.make_graph_from_config()
    apply = bool(args.apply)
    results = run_migration(graph, apply=apply, batch_size=args.batch)

    mode = "apply" if apply else "dry-run"
    logger.info("Participation-edge migration (%s)", mode)
    for k in sorted(results.keys()):
        logger.info("%s=%s", k, results[k])


if __name__ == "__main__":
    main()
