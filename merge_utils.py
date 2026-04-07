"""Utilities for authority-aware attribute conflict resolution."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textgraphx.authority import (
    EvidenceRecord,
    decide_conflict,
    normalize_evidence_source,
    resolve_authority_tier,
)


def resolve_attribute_conflict(
    existing_value: Optional[Any],
    incoming_value: Optional[Any],
    *,
    existing_source: str,
    incoming_source: str,
    existing_confidence: float = 0.0,
    incoming_confidence: float = 0.0,
    existing_tier: Optional[str] = None,
    incoming_tier: Optional[str] = None,
    conflict_policy: str = "additive",
) -> Dict[str, Any]:
    """Resolve an attribute conflict and return merge metadata.

    Returns:
      {
        action, has_conflict,
        value, source, confidence, authority_tier,
        conflict_value, conflict_source, conflict_confidence, conflict_tier
      }
    """
    normalized_existing_source = normalize_evidence_source(existing_source)
    normalized_incoming_source = normalize_evidence_source(incoming_source)
    existing_record = None
    incoming_record = None

    if existing_value is not None:
        existing_record = EvidenceRecord(
            value=str(existing_value),
            evidence_source=normalized_existing_source,
            authority_tier=resolve_authority_tier(normalized_existing_source, existing_tier),
            confidence=float(existing_confidence),
        )

    if incoming_value is not None:
        incoming_record = EvidenceRecord(
            value=str(incoming_value),
            evidence_source=normalized_incoming_source,
            authority_tier=resolve_authority_tier(normalized_incoming_source, incoming_tier),
            confidence=float(incoming_confidence),
        )

    decision = decide_conflict(existing_record, incoming_record, conflict_policy=conflict_policy)

    winner = decision.winner
    loser = decision.loser if decision.has_conflict else None

    return {
        "action": decision.action,
        "has_conflict": decision.has_conflict,
        "value": winner.value if winner else None,
        "source": winner.evidence_source if winner else None,
        "confidence": winner.confidence if winner else None,
        "authority_tier": winner.authority_tier if winner else None,
        "conflict_value": loser.value if loser else None,
        "conflict_source": loser.evidence_source if loser else None,
        "conflict_confidence": loser.confidence if loser else None,
        "conflict_tier": loser.authority_tier if loser else None,
    }
