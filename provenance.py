"""Utilities for confidence/provenance on inferred graph relationships."""

from __future__ import annotations

from typing import Any, Dict, Optional


_SOURCE_AUTHORITY_TIER = {
    # Primary authorities
    "allen_nlp_srl": "primary",
    "allennlp_srl": "primary",
    "temporal_phase": "primary",
    "ttk": "primary",
    "heideltime": "primary",
    "coref_service": "primary",
    "external_coref": "primary",
    # Secondary/derived authorities
    "tlinks_recognizer": "secondary",
    "event_enrichment": "secondary",
    "refinement": "secondary",
    "refinement_rule": "secondary",
    # Optional enrichment authorities
    "spacy": "support",
    "spacy_support": "support",
    "dbpedia_spotlight": "support",
    "dbpedia": "support",
    # Generic fallback
    "heuristic": "support",
}


def _normalize_evidence_source(evidence_source: str) -> str:
    source = str(evidence_source or "").strip().lower()
    if not source:
        raise ValueError("evidence_source must be non-empty")
    return source


def _resolve_authority_tier(evidence_source: str, authority_tier: Optional[str] = None) -> str:
    if authority_tier is not None:
        normalized = str(authority_tier).strip().lower()
        if normalized not in {"primary", "secondary", "support"}:
            raise ValueError("authority_tier must be one of: primary, secondary, support")
        return normalized

    source = _normalize_evidence_source(evidence_source)
    return _SOURCE_AUTHORITY_TIER.get(source, "support")


def stamp_inferred_relationships(
    graph: Any,
    rel_type: str,
    confidence: float,
    evidence_source: str,
    rule_id: str,
    authority_tier: Optional[str] = None,
    source_kind: str = "rule",
    conflict_policy: str = "additive",
    extra_properties: Optional[Dict[str, Any]] = None,
) -> int:
    """Stamp provenance/confidence properties on inferred relationships.

    Applies to all relationships of the requested type and is safe to run
    repeatedly. Returns the number of relationships touched.
    """
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    normalized_source = _normalize_evidence_source(evidence_source)
    normalized_tier = _resolve_authority_tier(normalized_source, authority_tier)
    normalized_kind = str(source_kind or "rule").strip().lower()
    normalized_policy = str(conflict_policy or "additive").strip().lower()
    if normalized_kind not in {"rule", "service", "model", "manual"}:
        raise ValueError("source_kind must be one of: rule, service, model, manual")
    if normalized_policy not in {"additive", "overwrite", "merge"}:
        raise ValueError("conflict_policy must be one of: additive, overwrite, merge")

    query = f"""
    MATCH ()-[r:{rel_type}]->()
    SET r.confidence = $confidence,
        r.evidence_source = $source,
        r.rule_id = $rule_id,
        r.authority_tier = $authority_tier,
        r.source_kind = $source_kind,
        r.conflict_policy = $conflict_policy,
        r.created_at = coalesce(r.created_at, datetime().epochMillis)
    RETURN count(r) AS c
    """

    params: Dict[str, Any] = {
        "confidence": float(confidence),
        "source": normalized_source,
        "rule_id": rule_id,
        "authority_tier": normalized_tier,
        "source_kind": normalized_kind,
        "conflict_policy": normalized_policy,
    }
    if extra_properties:
        for key, value in extra_properties.items():
            params[f"meta_{key}"] = value
            query = query.replace(
                "RETURN count(r) AS c",
                f"    , r.{key} = $meta_{key}\n    RETURN count(r) AS c",
            )

    rows = graph.run(
        query,
        params,
    ).data()
    if not rows:
        return 0
    return int(rows[0].get("c", 0))


def validate_inferred_relationship_provenance(graph: Any, rel_type: str) -> int:
    """Return the number of relationships missing required provenance fields."""
    query = f"""
    MATCH ()-[r:{rel_type}]->()
    WHERE r.confidence IS NULL
       OR r.evidence_source IS NULL
       OR r.rule_id IS NULL
       OR r.authority_tier IS NULL
       OR r.source_kind IS NULL
       OR r.conflict_policy IS NULL
    RETURN count(r) AS c
    """
    rows = graph.run(query, {}).data()
    if not rows:
        return 0
    return int(rows[0].get("c", 0))
