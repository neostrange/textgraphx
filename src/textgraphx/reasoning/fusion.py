"""Cross-sentence and cross-document fusion utilities."""

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
    MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)
    MATCH (s)-[:HAS_TOKEN]->(to1:TagOccurrence)-[:IN_MENTION]->(ne1:NamedEntity)-[:REFERS_TO]->(e1:Entity)
    MATCH (s)-[:HAS_TOKEN]->(to2:TagOccurrence)-[:IN_MENTION]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
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
    require_type_compatibility: bool = True,
) -> int:
    """Create `SAME_AS` links for entities that share stable external identity.

    Current baseline uses non-empty `kb_id` equality across distinct documents.
    """
    _validate_confidence(confidence)

    query = """
    MATCH (d1:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
            -[:IN_MENTION]->(:NamedEntity)-[:REFERS_TO]->(e1:Entity)
    MATCH (d2:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
            -[:IN_MENTION]->(:NamedEntity)-[:REFERS_TO]->(e2:Entity)
    WHERE d1.id <> d2.id
      AND e1 <> e2
      AND id(e1) < id(e2)
      AND e1.kb_id IS NOT NULL
      AND e1.kb_id <> ""
      AND e1.kb_id = e2.kb_id
      AND (
            $require_type_compatibility = false
            OR coalesce(e1.type, "") = ""
            OR coalesce(e2.type, "") = ""
            OR toUpper(coalesce(e1.type, "")) = toUpper(coalesce(e2.type, ""))
        )
    MERGE (e1)-[r:SAME_AS]->(e2)
    ON CREATE SET
      r.confidence = $confidence,
      r.evidence_source = $evidence_source,
      r.rule_id = $rule_id,
      r.type_compatibility_required = $require_type_compatibility,
      r.created_at = datetime()
    RETURN count(r) AS c
    """
    rows = graph.run(
        query,
        {
            "confidence": confidence,
            "evidence_source": evidence_source,
            "rule_id": rule_id,
            "require_type_compatibility": bool(require_type_compatibility),
        },
    ).data()
    return int(rows[0].get("c", 0)) if rows else 0


def propagate_coreference_identity_cross_document(
    graph,
    confidence: float = 0.72,
    evidence_source: str = "refinement_phase",
    rule_id: str = "cross_document_coref_identity_v1",
    require_type_compatibility: bool = True,
    min_key_length: int = 3,
) -> int:
    """Create `SAME_AS` links across documents using coref-derived identity keys.

    This pass complements `kb_id`-based fusion by using normalized mention
    heads/surface forms from coreference artifacts where a stable external id is
    unavailable. It is intentionally conservative and only links entities across
    distinct documents.
    """
    _validate_confidence(confidence)

    query = """
    MATCH (d1:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
                -[:IN_MENTION]->(m1)-[:REFERS_TO]->(e1:Entity)
    MATCH (d2:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
                -[:IN_MENTION]->(m2)-[:REFERS_TO]->(e2:Entity)
    WHERE d1.id <> d2.id
      AND e1 <> e2
      AND id(e1) < id(e2)
      AND (m1:NamedEntity OR m1:CorefMention OR m1:Antecedent)
      AND (m2:NamedEntity OR m2:CorefMention OR m2:Antecedent)
    WITH e1, e2,
         toLower(trim(coalesce(m1.head, m1.normal_term, m1.value, m1.text, ''))) AS k1,
         toLower(trim(coalesce(m2.head, m2.normal_term, m2.value, m2.text, ''))) AS k2
    WHERE k1 <> ''
      AND k2 <> ''
      AND k1 = k2
      AND size(k1) >= $min_key_length
      AND (coalesce(e1.kb_id, '') = '' OR coalesce(e2.kb_id, '') = '')
      AND (
            $require_type_compatibility = false
            OR coalesce(e1.type, '') = ''
            OR coalesce(e2.type, '') = ''
            OR toUpper(coalesce(e1.type, '')) = toUpper(coalesce(e2.type, ''))
        )
    MERGE (e1)-[r:SAME_AS]->(e2)
    ON CREATE SET
      r.confidence = $confidence,
      r.evidence_source = $evidence_source,
      r.rule_id = $rule_id,
      r.identity_key = k1,
      r.type_compatibility_required = $require_type_compatibility,
      r.created_at = datetime()
    RETURN count(r) AS c
    """
    rows = graph.run(
        query,
        {
            "confidence": confidence,
            "evidence_source": evidence_source,
            "rule_id": rule_id,
            "require_type_compatibility": bool(require_type_compatibility),
            "min_key_length": max(1, int(min_key_length)),
        },
    ).data()
    return int(rows[0].get("c", 0)) if rows else 0


__all__ = [
    "fuse_entities_cross_document",
    "fuse_entities_cross_sentence",
    "propagate_coreference_identity_cross_document",
]