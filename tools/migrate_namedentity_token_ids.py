"""Migration helper: compute token-index based ids for NamedEntity nodes.

This script runs in two modes:
 - --dry-run : compute mappings and print a summary, no DB writes
 - --apply   : apply token_id, token_start, token_end properties to NamedEntity nodes

It uses the project's neo4j_client.make_graph_from_config() for connection.
"""
from __future__ import annotations

import argparse
import math
from typing import Dict, List, Optional, Tuple

from textgraphx import neo4j_client
import logging

# module logger
logger = logging.getLogger(__name__)


def find_tok_indices_for_ne(G, ne_id: str, start_index: int, end_index: int) -> Optional[Tuple[int, int]]:
    """Find token start/end tok_index_doc for a NamedEntity by char offsets.

    Returns (tok_start, tok_end) or None when matching tokens cannot be found.
    """
    # derive document prefix from NamedEntity id pattern: <doc>_...   (safe fallback)
    doc_prefix = ne_id.split("_")[0]

    # Exact start token match
    q_start = (
        "MATCH (t:TagOccurrence)"
        " WHERE t.id STARTS WITH $dp AND t.index = $start_index"
        " RETURN t.tok_index_doc AS tok_start LIMIT 1"
    )
    res = G.run(q_start, {"dp": doc_prefix + "_", "start_index": start_index}).data()
    tok_start = res[0]["tok_start"] if res else None

    # Exact end token match
    q_end = (
        "MATCH (t:TagOccurrence)"
        " WHERE t.id STARTS WITH $dp AND t.end_index = $end_index"
        " RETURN t.tok_index_doc AS tok_end LIMIT 1"
    )
    res2 = G.run(q_end, {"dp": doc_prefix + "_", "end_index": end_index}).data()
    tok_end = res2[0]["tok_end"] if res2 else None

    # Fallbacks
    if tok_start is None:
        # try to match the first token whose index >= start_index
        qfs = (
            "MATCH (t:TagOccurrence)"
            " WHERE t.id STARTS WITH $dp AND t.index <= $start_index"
            " RETURN t.tok_index_doc AS tok_start ORDER BY t.tok_index_doc ASC LIMIT 1"
        )
        rfs = G.run(qfs, {"dp": doc_prefix + "_", "start_index": start_index}).data()
        tok_start = rfs[0]["tok_start"] if rfs else None

    if tok_end is None:
        # fallback: greatest token whose index <= end_index
        qfe = (
            "MATCH (t:TagOccurrence)"
            " WHERE t.id STARTS WITH $dp AND t.index <= $end_index"
            " RETURN t.tok_index_doc AS tok_end ORDER BY t.tok_index_doc DESC LIMIT 1"
        )
        rfe = G.run(qfe, {"dp": doc_prefix + "_", "end_index": end_index}).data()
        tok_end = rfe[0]["tok_end"] if rfe else None

    if tok_start is None or tok_end is None:
        return None

    # ensure ordering
    if tok_start > tok_end:
        tok_start, tok_end = tok_end, tok_start

    return int(tok_start), int(tok_end)


def collect_namedentities(G, batch: int = 200) -> List[Dict]:
    """Collect NamedEntity metadata in batches to avoid heavy transactions."""
    total = G.run("MATCH (n:NamedEntity) RETURN count(n) AS cnt").data()[0]["cnt"]
    total = int(total)
    results = []
    for skip in range(0, total, batch):
        q = (
            "MATCH (n:NamedEntity)"
            " RETURN n.id AS id, n.index AS start_index, n.end_index AS end_index, n.type AS type"
            " SKIP $skip LIMIT $limit"
        )
        rows = G.run(q, {"skip": skip, "limit": batch}).data()
        for r in rows:
            results.append(r)
    return results


def compute_mappings(G, nes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Compute token-index mappings for a list of NamedEntity rows.

    Returns (mappings, skipped)
    """
    mappings = []
    skipped = []
    for ne in nes:
        ne_id = ne.get("id")
        start = ne.get("start_index")
        end = ne.get("end_index")
        ne_type = ne.get("type") or (ne_id.split("_")[-1] if ne_id else "UNKNOWN")
        if ne_id is None or start is None or end is None:
            skipped.append({"id": ne_id, "reason": "missing indices"})
            continue
        res = find_tok_indices_for_ne(G, ne_id, int(start), int(end))
        if not res:
            skipped.append({"id": ne_id, "reason": "no token match"})
            continue
        tok_start, tok_end = res
        token_id = f"{ne_id.split('_')[0]}_{tok_start}_{tok_end}_{ne_type}"
        mappings.append({
            "ne_id": ne_id,
            "token_id": token_id,
            "tok_start": tok_start,
            "tok_end": tok_end,
            "type": ne_type,
        })
    return mappings, skipped


def apply_mappings(G, mappings: List[Dict], batch: int = 100) -> Tuple[int, List[Dict]]:
    """Apply token_id, token_start, token_end properties to NamedEntity nodes."""
    applied = 0
    errors = []
    for i in range(0, len(mappings), batch):
        chunk = mappings[i : i + batch]
        for m in chunk:
            q = (
                "MATCH (n:NamedEntity {id:$ne_id})"
                " SET n.token_id = $token_id, n.token_start = $tok_start, n.token_end = $tok_end"
                " RETURN n.id AS id"
            )
            try:
                r = G.run(q, {"ne_id": m["ne_id"], "token_id": m["token_id"], "tok_start": m["tok_start"], "tok_end": m["tok_end"]}).data()
                if r:
                    applied += 1
            except Exception as e:
                errors.append({"ne_id": m.get("ne_id"), "error": str(e)})
    return applied, errors


def main():
    parser = argparse.ArgumentParser(description="Map NamedEntity char offsets to token-index ids")
    parser.add_argument("--dry-run", action="store_true", help="Compute mappings and print summary without writing")
    parser.add_argument("--apply", action="store_true", help="Apply computed mappings to the DB")
    parser.add_argument("--batch", type=int, default=200, help="Batch size for reads (default 200)")
    args = parser.parse_args()

    G = neo4j_client.make_graph_from_config()
    logger.info("Collecting NamedEntity nodes...")
    nes = collect_namedentities(G, batch=args.batch)
    logger.info("Found %d NamedEntity candidates", len(nes))

    logger.info("Computing token-index mappings (this may run many small queries)...")
    mappings, skipped = compute_mappings(G, nes)
    logger.info("Computed mappings: %d; Skipped: %d", len(mappings), len(skipped))

    # detect duplicates among computed token_ids
    seen = {}
    duplicates = []
    for m in mappings:
        if m["token_id"] in seen:
            duplicates.append({"token_id": m["token_id"], "first": seen[m["token_id"]], "second": m["ne_id"]})
        else:
            seen[m["token_id"]] = m["ne_id"]

    if duplicates:
        logger.warning("duplicate computed token_ids detected (first 10): %s", duplicates[:10])

    # print a small sample
    sample_n = min(20, len(mappings))
    if sample_n:
        logger.info("Sample mappings:")
        for s in mappings[:sample_n]:
            logger.info("%s  ->  %s (tok_start=%s, tok_end=%s)", s['ne_id'], s['token_id'], s['tok_start'], s['tok_end'])

    if args.dry_run:
        logger.info("Dry-run complete. No changes applied.")
        return

    if not args.apply:
        logger.info("No --apply flag provided. Exiting without applying changes.")
        return

    if duplicates:
        logger.error("Aborting apply because duplicate token_ids were computed. Resolve duplicates first.")
        return

    logger.info("Applying mappings to NamedEntity nodes...")
    applied, errors = apply_mappings(G, mappings, batch=100)
    logger.info("Applied to %d nodes. Errors: %d", applied, len(errors))
    if errors:
        for e in errors[:10]:
            logger.error("%s", e)


if __name__ == "__main__":
    main()
