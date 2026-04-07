"""Constraint-based temporal consistency utilities for TLINK graphs.

This module applies conservative, high-precision consistency operations:
1. Materialize missing inverse TLINKs for canonical inverse pairs.
2. Suppress contradictory bidirectional TLINKs of same relation type.
"""

from __future__ import annotations

from typing import Any, Dict


INVERSE_REL_MAP: Dict[str, str] = {
    "BEFORE": "AFTER",
    "AFTER": "BEFORE",
    "INCLUDES": "IS_INCLUDED",
    "IS_INCLUDED": "INCLUDES",
    "BEGINS": "BEGUN_BY",
    "BEGUN_BY": "BEGINS",
    "ENDS": "ENDED_BY",
    "ENDED_BY": "ENDS",
    "IDENTITY": "IDENTITY",
}


def _count_result(rows, key: str) -> int:
    if not rows:
        return 0
    return int(rows[0].get(key, 0) or 0)


def materialize_inverse_tlinks(graph: Any) -> int:
    """Create missing inverse TLINK edges for canonical relation pairs."""
    query = """
    MATCH (a)-[r:TLINK]->(b)
    WHERE coalesce(r.suppressed, false) = false
      AND coalesce(r.relTypeCanonical, r.relType) IN $supported
    WITH a, b, r,
         coalesce(r.relTypeCanonical, r.relType) AS rel,
         coalesce(r.confidence, 0.0) AS conf
    WITH a, b, rel, conf,
         CASE rel
            WHEN 'BEFORE' THEN 'AFTER'
            WHEN 'AFTER' THEN 'BEFORE'
            WHEN 'INCLUDES' THEN 'IS_INCLUDED'
            WHEN 'IS_INCLUDED' THEN 'INCLUDES'
            WHEN 'BEGINS' THEN 'BEGUN_BY'
            WHEN 'BEGUN_BY' THEN 'BEGINS'
            WHEN 'ENDS' THEN 'ENDED_BY'
            WHEN 'ENDED_BY' THEN 'ENDS'
            WHEN 'IDENTITY' THEN 'IDENTITY'
            ELSE NULL
         END AS inverse_rel
    WHERE inverse_rel IS NOT NULL
    MERGE (b)-[inv:TLINK {relType: inverse_rel}]->(a)
    ON CREATE SET inv.relTypeCanonical = inverse_rel,
                  inv.source = 'constraint_solver',
                  inv.rule_id = 'inverse_consistency',
                  inv.evidence_source = 'tlinks_constraint_solver',
                  inv.confidence = conf,
                  inv.createdByConstraintSolver = true,
                  inv.createdAt = datetime().epochMillis
    RETURN count(CASE WHEN inv.createdByConstraintSolver = true THEN 1 END) AS created
    """
    rows = graph.run(query, {"supported": list(INVERSE_REL_MAP.keys())}).data()
    return _count_result(rows, "created")


def suppress_bidirectional_same_rel_conflicts(graph: Any, shadow_only: bool = False) -> int:
    """Suppress contradictory bidirectional same-rel TLINKs.

    Example contradiction: a-[:TLINK {relType:'BEFORE'}]->b and
    b-[:TLINK {relType:'BEFORE'}]->a.
    """
    query_prefix = """
    MATCH (a)-[r1:TLINK]->(b), (b)-[r2:TLINK]->(a)
    WHERE id(r1) < id(r2)
      AND coalesce(r1.suppressed, false) = false
      AND coalesce(r2.suppressed, false) = false
      AND coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE')
          = coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE')
    WITH r1, r2,
         coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS rel,
         coalesce(r1.confidence, 0.0) AS c1,
         coalesce(r2.confidence, 0.0) AS c2
    WHERE rel IN ['BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'BEGINS', 'BEGUN_BY', 'ENDS', 'ENDED_BY']
    WITH r1, r2, rel,
         CASE
            WHEN c1 > c2 THEN r2
            WHEN c2 > c1 THEN r1
            WHEN id(r1) < id(r2) THEN r2
            ELSE r1
         END AS loser
    """

    if shadow_only:
        query = query_prefix + "RETURN count(DISTINCT loser) AS would_suppress"
        rows = graph.run(query, {}).data()
        return _count_result(rows, "would_suppress")

    query = query_prefix + """
    SET loser.suppressed = true,
        loser.suppressedBy = 'tlink_constraint_solver',
        loser.suppressedAt = datetime().epochMillis,
        loser.suppressionReason = 'bidirectional_same_rel_conflict'
    RETURN count(DISTINCT loser) AS suppressed
    """
    rows = graph.run(query, {}).data()
    return _count_result(rows, "suppressed")


def solve_tlink_constraints(graph: Any, shadow_only: bool = False) -> Dict[str, int]:
    """Run conservative TLINK constraint solving and return summary counts."""
    inverse_created = materialize_inverse_tlinks(graph)
    bidirectional_conflicts = suppress_bidirectional_same_rel_conflicts(
        graph,
        shadow_only=shadow_only,
    )
    return {
        "inverse_created": int(inverse_created),
        "bidirectional_conflicts": int(bidirectional_conflicts),
    }
