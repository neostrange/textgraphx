"""Authority and conflict-resolution helpers for evidence integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

_VALID_TIERS = ("primary", "secondary", "support")


SOURCE_AUTHORITY_TIER = {
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
    # Optional/support authorities
    "spacy": "support",
    "spacy_support": "support",
    "dbpedia_spotlight": "support",
    "dbpedia": "support",
    "heuristic": "support",
}


def normalize_evidence_source(evidence_source: str) -> str:
    source = str(evidence_source or "").strip().lower()
    if not source:
        raise ValueError("evidence_source must be non-empty")
    return source


def resolve_authority_tier(evidence_source: str, authority_tier: Optional[str] = None) -> str:
    if authority_tier is not None:
        tier = str(authority_tier).strip().lower()
        if tier not in _VALID_TIERS:
            raise ValueError("authority_tier must be one of: primary, secondary, support")
        return tier
    return SOURCE_AUTHORITY_TIER.get(normalize_evidence_source(evidence_source), "support")


def authority_rank(authority_tier: str) -> int:
    tier = str(authority_tier or "").strip().lower()
    order = {"support": 0, "secondary": 1, "primary": 2}
    if tier not in order:
        raise ValueError("authority_tier must be one of: primary, secondary, support")
    return order[tier]


@dataclass(frozen=True)
class EvidenceRecord:
    value: str
    evidence_source: str
    authority_tier: str
    confidence: float = 0.0


def choose_authoritative_evidence(records: Iterable[EvidenceRecord]) -> Optional[EvidenceRecord]:
    """Choose the best evidence record deterministically.

    Priority order:
    1) higher authority tier
    2) higher confidence
    3) lexical tie-break on source and value for determinism
    """
    items = list(records)
    if not items:
        return None

    def _key(item: EvidenceRecord):
        return (
            authority_rank(item.authority_tier),
            float(item.confidence),
            str(item.evidence_source or "").lower(),
            str(item.value or "").lower(),
        )

    return sorted(items, key=_key, reverse=True)[0]
