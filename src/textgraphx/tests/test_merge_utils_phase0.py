"""Phase-0 tests for authority-aware merge utility."""

import pytest

from textgraphx.reasoning.merge_utils import resolve_attribute_conflict
from textgraphx.reasoning.merge_utils import resolve_attribute_conflict as canonical_resolve_attribute_conflict


@pytest.mark.unit
def test_root_merge_utils_wrapper_reexports_canonical_resolver():
    assert resolve_attribute_conflict is canonical_resolve_attribute_conflict


@pytest.mark.unit
def test_resolve_attribute_conflict_prefers_primary_even_with_lower_confidence():
    resolved = resolve_attribute_conflict(
        "PAST",
        "PRESENT",
        existing_source="temporal_phase",
        incoming_source="event_enrichment",
        existing_confidence=0.2,
        incoming_confidence=0.99,
        conflict_policy="additive",
    )

    assert resolved["value"] == "PAST"
    assert resolved["source"] == "temporal_phase"
    assert resolved["has_conflict"] is True
    assert resolved["conflict_value"] == "PRESENT"


@pytest.mark.unit
def test_resolve_attribute_conflict_inserts_when_existing_missing():
    resolved = resolve_attribute_conflict(
        None,
        "FUTURE",
        existing_source="temporal_phase",
        incoming_source="event_enrichment",
        existing_confidence=0.0,
        incoming_confidence=0.7,
    )

    assert resolved["action"] == "insert"
    assert resolved["value"] == "FUTURE"
    assert resolved["source"] == "event_enrichment"


@pytest.mark.unit
def test_resolve_attribute_conflict_overwrite_replaces_when_incoming_wins():
    resolved = resolve_attribute_conflict(
        "POSSIBLE",
        "CERTAIN",
        existing_source="spacy_support",
        incoming_source="event_enrichment",
        existing_confidence=0.2,
        incoming_confidence=0.9,
        existing_tier="support",
        incoming_tier="secondary",
        conflict_policy="overwrite",
    )

    assert resolved["action"] == "replace"
    assert resolved["value"] == "CERTAIN"
    assert resolved["source"] == "event_enrichment"


@pytest.mark.unit
def test_resolve_attribute_conflict_rejects_empty_source():
    with pytest.raises(ValueError):
        resolve_attribute_conflict(
            "X",
            "Y",
            existing_source="",
            incoming_source="event_enrichment",
        )
