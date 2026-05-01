"""Cross-framework SRL frame fusion.

This module detects when a PROPBANK (verbal) Frame and a NOMBANK (nominal) Frame
refer to the same underlying situation and creates a deterministic
``ALIGNS_WITH`` edge between them.

Alignment criteria (all must hold):
1. The two frames share the same document (``doc_id``).
2. Their headword lemmas match (case-insensitive).
3. At least one of the following span-proximity rules holds:
   a. The frames' head token indices are within ``TOKEN_WINDOW`` tokens of each
      other, OR
   b. The nominal frame's head token is reachable from the verbal frame's head
      token within the dependency graph (handled by callers who pass spans).

The alignment key is derived deterministically from the two frame IDs so that
repeated runs produce an idempotent MERGE.

Design notes
------------
- The ``ALIGNS_WITH`` edge is optional-tier; downstream phases may consume it
  but must not require it.
- Light-verb construction detection: when the verbal frame's headword is a
  light verb (``make``, ``give``, ``take``, ``have``, ``do``, ``get``) AND the
  nominal frame is a deverbal noun, the verbal frame is downgraded to
  ``LIGHT_VERB_HOST=true``.  The nominal frame becomes the canonical event.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tokens allowed between verbal and nominal predicate heads for proximity-based
# alignment.
TOKEN_WINDOW = 5

# English light verbs whose argument structure is vacuous; the nominal
# co-argument carries the real event meaning.
_LIGHT_VERBS = frozenset(
    {"make", "give", "take", "have", "do", "get", "put", "set", "keep"}
)


def _alignment_key(frame_id_a: str, frame_id_b: str) -> str:
    """Deterministic alignment key from two frame ids (order-independent)."""
    lo, hi = sorted([frame_id_a, frame_id_b])
    return f"align__{lo}__{hi}"


def maybe_align_frames(
    graph,
    doc_id,
    verbal_frame_id: str,
    verbal_headword: str,
    verbal_head_index: int,
    verbal_sense_conf: Optional[float],
    nominal_frame_id: str,
    nominal_headword: str,
    nominal_head_index: int,
    nominal_sense_conf: Optional[float],
) -> bool:
    """Create an ``ALIGNS_WITH`` edge when the two frames describe the same event.

    Parameters
    ----------
    graph:
        Graph connection object with a ``.run(query, params)`` method.
    doc_id:
        Document identifier (used for scoping and logging only).
    verbal_frame_id, nominal_frame_id:
        Node ``id`` properties of the two Frame nodes.
    verbal_headword, nominal_headword:
        Lexical head strings; compared case-insensitively.
    verbal_head_index, nominal_head_index:
        Token indices of the respective head tokens.
    verbal_sense_conf, nominal_sense_conf:
        Confidence floats from the respective services (may be ``None``).

    Returns
    -------
    bool
        ``True`` if an ``ALIGNS_WITH`` edge was created, ``False`` otherwise.
    """
    if verbal_headword.lower() != nominal_headword.lower():
        return False

    if abs(verbal_head_index - nominal_head_index) > TOKEN_WINDOW:
        return False

    # Combined confidence for the edge (geometric mean when both available)
    if verbal_sense_conf is not None and nominal_sense_conf is not None:
        import math
        confidence = math.sqrt(verbal_sense_conf * nominal_sense_conf)
    elif verbal_sense_conf is not None:
        confidence = verbal_sense_conf
    elif nominal_sense_conf is not None:
        confidence = nominal_sense_conf
    else:
        confidence = None

    is_light_verb = verbal_headword.lower() in _LIGHT_VERBS
    alignment_key = _alignment_key(verbal_frame_id, nominal_frame_id)

    query = """
    MATCH (vf:Frame {id: $verbal_id})
    MATCH (nf:Frame {id: $nominal_id})
    MERGE (vf)-[r:ALIGNS_WITH {alignment_key: $alignment_key}]->(nf)
    SET r.confidence = $confidence
    FOREACH (_ IN CASE WHEN $is_light_verb THEN [1] ELSE [] END |
        SET vf.is_light_verb_host = true
    )
    RETURN id(r) AS rel_id
    """
    params = {
        "verbal_id": verbal_frame_id,
        "nominal_id": nominal_frame_id,
        "alignment_key": alignment_key,
        "confidence": confidence,
        "is_light_verb": is_light_verb,
    }
    graph.run(query, params)
    logger.debug(
        "ALIGNS_WITH created: verbal=%s nominal=%s key=%s conf=%s light_verb=%s",
        verbal_frame_id, nominal_frame_id, alignment_key, confidence, is_light_verb,
    )
    return True


def run_cross_framework_alignment(graph, doc_id: str) -> int:
    """Post-ingestion alignment pass over all frames in a document.

    Queries the graph for PROPBANK + NOMBANK Frame pairs in the same document
    whose headwords match and head token indices are within ``TOKEN_WINDOW``.
    Creates ``ALIGNS_WITH`` edges for each qualifying pair.

    Parameters
    ----------
    graph:
        Graph connection with ``.run(query, params)`` method.
    doc_id:
        Document identifier to scope the query.

    Returns
    -------
    int
        Number of ``ALIGNS_WITH`` edges created or merged.
    """
    # Find candidate pairs: same headword (case-insensitive), within window
    find_query = """
    MATCH (vf:Frame {framework: 'PROPBANK'})
          -[:IN_FRAME|PARTICIPATES_IN*0..1]-()
          -[:HAS_TOKEN|CONTAINS_SENTENCE*0..2]-(:AnnotatedText {id: $doc_id})
    MATCH (nf:Frame {framework: 'NOMBANK'})
          -[:IN_FRAME|PARTICIPATES_IN*0..1]-()
          -[:HAS_TOKEN|CONTAINS_SENTENCE*0..2]-(:AnnotatedText {id: $doc_id})
    WHERE toLower(vf.headword) = toLower(nf.headword)
      AND abs(vf.headTokenIndex - nf.headTokenIndex) <= $window
      AND NOT (vf)-[:ALIGNS_WITH]->(nf)
    RETURN vf.id AS verbal_id,  vf.headword AS verbal_hw,
           vf.headTokenIndex AS verbal_idx, vf.sense_conf AS verbal_conf,
           nf.id AS nominal_id, nf.headword AS nominal_hw,
           nf.headTokenIndex AS nominal_idx, nf.sense_conf AS nominal_conf
    """
    rows = graph.run(find_query, {"doc_id": doc_id, "window": TOKEN_WINDOW}).data()
    count = 0
    for row in rows:
        created = maybe_align_frames(
            graph=graph,
            doc_id=doc_id,
            verbal_frame_id=row["verbal_id"],
            verbal_headword=row["verbal_hw"],
            verbal_head_index=row["verbal_idx"],
            verbal_sense_conf=row["verbal_conf"],
            nominal_frame_id=row["nominal_id"],
            nominal_headword=row["nominal_hw"],
            nominal_head_index=row["nominal_idx"],
            nominal_sense_conf=row["nominal_conf"],
        )
        if created:
            count += 1
    logger.info(
        "run_cross_framework_alignment doc_id=%s: %d ALIGNS_WITH edges created",
        doc_id, count,
    )
    return count
