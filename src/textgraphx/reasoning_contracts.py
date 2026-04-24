"""Compatibility wrapper for the canonical reasoning contracts module."""

from textgraphx.reasoning.contracts import (
    canonical_event_attribute_vocabulary,
    count_endpoint_violations,
    load_ontology_contract,
    normalize_event_attr,
    relation_endpoint_contract,
    temporal_reasoning_profile,
)

__all__ = [
    "canonical_event_attribute_vocabulary",
    "count_endpoint_violations",
    "load_ontology_contract",
    "normalize_event_attr",
    "relation_endpoint_contract",
    "temporal_reasoning_profile",
]
