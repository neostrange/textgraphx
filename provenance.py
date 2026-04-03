"""Utilities for confidence/provenance on inferred graph relationships."""

from __future__ import annotations

from typing import Any


def stamp_inferred_relationships(
    graph: Any,
    rel_type: str,
    confidence: float,
    evidence_source: str,
    rule_id: str,
) -> int:
    """Stamp provenance/confidence properties on inferred relationships.

    Applies to all relationships of the requested type and is safe to run
    repeatedly. Returns the number of relationships touched.
    """
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    query = f"""
    MATCH ()-[r:{rel_type}]->()
    SET r.confidence = $confidence,
        r.evidence_source = $source,
        r.rule_id = $rule_id,
        r.created_at = coalesce(r.created_at, datetime().epochMillis)
    RETURN count(r) AS c
    """

    rows = graph.run(
        query,
        {
            "confidence": float(confidence),
            "source": evidence_source,
            "rule_id": rule_id,
        },
    ).data()
    if not rows:
        return 0
    return int(rows[0].get("c", 0))
