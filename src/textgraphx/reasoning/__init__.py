"""Canonical reasoning support package for authority, provenance, and contracts."""

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
from textgraphx.reasoning.confidence import (
    DEFAULT_EVIDENCE_WEIGHTS,
    calibrate_confidence,
    compute_evidence_weighted_confidence,
)
from textgraphx.reasoning.contracts import (
    canonical_event_attribute_vocabulary,
    count_endpoint_violations,
    load_ontology_contract,
    normalize_event_attr,
    relation_endpoint_contract,
    temporal_reasoning_profile,
)
from textgraphx.reasoning.merge_utils import resolve_attribute_conflict
from textgraphx.reasoning.provenance import (
    stamp_inferred_relationships,
    validate_inferred_relationship_provenance,
)

__all__ = [
    "ConflictDecision",
    "DEFAULT_EVIDENCE_WEIGHTS",
    "EvidenceRecord",
    "SOURCE_AUTHORITY_TIER",
    "authority_rank",
    "calibrate_confidence",
    "canonical_event_attribute_vocabulary",
    "choose_authoritative_evidence",
    "compute_evidence_weighted_confidence",
    "count_endpoint_violations",
    "decide_conflict",
    "load_ontology_contract",
    "normalize_evidence_source",
    "normalize_event_attr",
    "relation_endpoint_contract",
    "resolve_attribute_conflict",
    "resolve_authority_tier",
    "stamp_inferred_relationships",
    "temporal_reasoning_profile",
    "validate_inferred_relationship_provenance",
]