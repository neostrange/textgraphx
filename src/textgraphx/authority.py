"""Compatibility wrapper for the canonical reasoning authority module."""

from textgraphx.reasoning.authority import (
    ConflictDecision,
    EvidenceRecord,
    SOURCE_AUTHORITY_TIER,
    authority_rank,
    choose_authoritative_evidence,
    decide_conflict,
    normalize_evidence_source,
    resolve_authority_tier,
)

__all__ = [
    "ConflictDecision",
    "EvidenceRecord",
    "SOURCE_AUTHORITY_TIER",
    "authority_rank",
    "choose_authoritative_evidence",
    "decide_conflict",
    "normalize_evidence_source",
    "resolve_authority_tier",
]
