"""Cross-sentence and cross-document fusion utilities.

These helpers add coherence relationships without rewriting existing entity links.
They are idempotent and safe to run repeatedly.
"""

from __future__ import annotations

from typing import Optional


def _validate_confidence(confidence: float) -> None:
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


def fuse_entities_cross_sentence(
    graph,
    doc_id: Optional[str] = None,
    confidence: float = 0.65,
    evidence_source: str = "refinement_phase",
    rule_id: str = "cross_sentence_cooccurrence_v1",
) -> int:
    """Create `CO_OCCURS_WITH` links for entities seen in nearby sentence context.

    If `doc_id` is provided, fusion is limited to one document.
    """
    _validate_confidence(confidence)

    query = """
    MATCH (d:AnnotatedText)-[:CONTAINS]->(s:Sentence)
    MATCH (s)<-[:PARTICIPATES_IN]-(to1:TagOccurrence)-[:PARTICIPATES_IN]->(ne1:NamedEntity)-[:REFERS_TO]->(e1:Entity)
    MATCH (s)<-[:PARTICIPATES_IN]-(to2:TagOccurrence)-[:PARTICIPATES_IN]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
    WHERE e1 <> e2
      AND id(e1) < id(e2)
      AND ($doc_id IS NULL OR d.id = $doc_id)
    MERGE (e1)-[r:CO_OCCURS_WITH]->(e2)
    ON CREATE SET
      r.confidence = $confidence,
      r.evidence_source = $evidence_source,
      r.rule_id = $rule_id,
      r.created_at = datetime()
    RETURN count(r) AS c
    """
    rows = graph.run(
        query,
        {
            "doc_id": doc_id,
            "confidence": confidence,
            "evidence_source": evidence_source,
            "rule_id": rule_id,
        },
    ).data()
    return int(rows[0].get("c", 0)) if rows else 0


def fuse_entities_cross_document(
    graph,
    confidence: float = 0.8,
    evidence_source: str = "refinement_phase",
    rule_id: str = "cross_document_same_kbid_v1",
) -> int:
    """Create `SAME_AS` links for entities that share stable external identity.

    Current baseline uses non-empty `kb_id` equality across distinct documents.
    """
    _validate_confidence(confidence)

    query = """
    MATCH (d1:AnnotatedText)-[:CONTAINS]->(:Sentence)<-[:PARTICIPATES_IN]-(:TagOccurrence)
          -[:PARTICIPATES_IN]->(:NamedEntity)-[:REFERS_TO]->(e1:Entity)
    MATCH (d2:AnnotatedText)-[:CONTAINS]->(:Sentence)<-[:PARTICIPATES_IN]-(:TagOccurrence)
          -[:PARTICIPATES_IN]->(:NamedEntity)-[:REFERS_TO]->(e2:Entity)
    WHERE d1.id <> d2.id
      AND e1 <> e2
      AND id(e1) < id(e2)
      AND e1.kb_id IS NOT NULL
      AND e1.kb_id <> ""
      AND e1.kb_id = e2.kb_id
    MERGE (e1)-[r:SAME_AS]->(e2)
    ON CREATE SET
      r.confidence = $confidence,
      r.evidence_source = $evidence_source,
      r.rule_id = $rule_id,
      r.created_at = datetime()
    RETURN count(r) AS c
    """
    rows = graph.run(
        query,
        {
            "confidence": confidence,
            "evidence_source": evidence_source,
            "rule_id": rule_id,
        },
    ).data()
    return int(rows[0].get("c", 0)) if rows else 0
