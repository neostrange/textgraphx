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


@dataclass(frozen=True)
class ConflictDecision:
    action: str
    winner: Optional[EvidenceRecord]
    loser: Optional[EvidenceRecord]
    has_conflict: bool


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


def decide_conflict(
    existing: Optional[EvidenceRecord],
    incoming: Optional[EvidenceRecord],
    conflict_policy: str = "additive",
) -> ConflictDecision:
    """Return deterministic action for conflicting evidence records.

    Policies:
    - additive: keep both values and expose a preferred winner.
    - overwrite: replace only if incoming outranks existing.
    - merge: keep both and expose a preferred winner (alias of additive for now).
    """
    policy = str(conflict_policy or "additive").strip().lower()
    if policy not in {"additive", "overwrite", "merge"}:
        raise ValueError("conflict_policy must be one of: additive, overwrite, merge")

    if existing is None and incoming is None:
        return ConflictDecision(action="noop", winner=None, loser=None, has_conflict=False)
    if existing is None:
        return ConflictDecision(action="insert", winner=incoming, loser=None, has_conflict=False)
    if incoming is None:
        return ConflictDecision(action="keep", winner=existing, loser=None, has_conflict=False)

    has_conflict = str(existing.value) != str(incoming.value)
    winner = choose_authoritative_evidence([existing, incoming])
    loser = incoming if winner == existing else existing

    if not has_conflict:
        return ConflictDecision(action="noop", winner=winner, loser=None, has_conflict=False)

    if policy in {"additive", "merge"}:
        return ConflictDecision(action="coexist", winner=winner, loser=loser, has_conflict=True)

    # overwrite policy: only replace if incoming wins.
    if winner == incoming:
        return ConflictDecision(action="replace", winner=winner, loser=loser, has_conflict=True)
    return ConflictDecision(action="keep", winner=winner, loser=loser, has_conflict=True)
