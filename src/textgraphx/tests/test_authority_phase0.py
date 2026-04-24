"""Unit tests for authority precedence and deterministic evidence selection."""

import pytest

from textgraphx.authority import resolve_authority_tier
from textgraphx.reasoning.authority import resolve_authority_tier as canonical_resolve_authority_tier


@pytest.mark.unit
def test_root_authority_wrapper_reexports_canonical_resolve_authority_tier():
    assert resolve_authority_tier is canonical_resolve_authority_tier


@pytest.mark.unit
def test_resolve_authority_tier_defaults_by_source():
    assert resolve_authority_tier("allen_nlp_srl") == "primary"
    assert resolve_authority_tier("event_enrichment") == "secondary"
    assert resolve_authority_tier("spacy_support") == "support"


@pytest.mark.unit
def test_resolve_authority_tier_rejects_invalid_explicit_tier():
    from textgraphx.authority import resolve_authority_tier

    with pytest.raises(ValueError):
        resolve_authority_tier("spacy", authority_tier="invalid")


@pytest.mark.unit
def test_choose_authoritative_evidence_prefers_higher_tier_then_confidence():
    from textgraphx.authority import EvidenceRecord, choose_authoritative_evidence

    winner = choose_authoritative_evidence(
        [
            EvidenceRecord(value="X", evidence_source="spacy_support", authority_tier="support", confidence=0.99),
            EvidenceRecord(value="Y", evidence_source="event_enrichment", authority_tier="secondary", confidence=0.60),
            EvidenceRecord(value="Z", evidence_source="allen_nlp_srl", authority_tier="primary", confidence=0.20),
        ]
    )

    assert winner is not None
    assert winner.value == "Z"


@pytest.mark.unit
def test_choose_authoritative_evidence_is_deterministic_for_ties():
    from textgraphx.authority import EvidenceRecord, choose_authoritative_evidence

    winner = choose_authoritative_evidence(
        [
            EvidenceRecord(value="beta", evidence_source="src_b", authority_tier="secondary", confidence=0.5),
            EvidenceRecord(value="alpha", evidence_source="src_a", authority_tier="secondary", confidence=0.5),
        ]
    )

    assert winner is not None
    assert winner.evidence_source == "src_b"


@pytest.mark.unit
def test_decide_conflict_additive_keeps_both_with_winner():
    from textgraphx.authority import EvidenceRecord, decide_conflict

    existing = EvidenceRecord(
        value="PAST",
        evidence_source="spacy_support",
        authority_tier="support",
        confidence=0.9,
    )
    incoming = EvidenceRecord(
        value="PRESENT",
        evidence_source="allen_nlp_srl",
        authority_tier="primary",
        confidence=0.2,
    )

    decision = decide_conflict(existing, incoming, conflict_policy="additive")
    assert decision.has_conflict is True
    assert decision.action == "coexist"
    assert decision.winner == incoming


@pytest.mark.unit
def test_decide_conflict_overwrite_replaces_only_when_incoming_wins():
    from textgraphx.authority import EvidenceRecord, decide_conflict

    existing = EvidenceRecord(
        value="PRESENT",
        evidence_source="allen_nlp_srl",
        authority_tier="primary",
        confidence=0.9,
    )
    incoming = EvidenceRecord(
        value="PAST",
        evidence_source="spacy_support",
        authority_tier="support",
        confidence=0.99,
    )

    decision = decide_conflict(existing, incoming, conflict_policy="overwrite")
    assert decision.has_conflict is True
    assert decision.action == "keep"
    assert decision.winner == existing


@pytest.mark.unit
def test_decide_conflict_handles_missing_records_and_invalid_policy():
    from textgraphx.authority import EvidenceRecord, decide_conflict

    incoming = EvidenceRecord(
        value="X",
        evidence_source="event_enrichment",
        authority_tier="secondary",
        confidence=0.5,
    )

    inserted = decide_conflict(None, incoming)
    assert inserted.action == "insert"
    assert inserted.winner == incoming

    with pytest.raises(ValueError):
        decide_conflict(incoming, incoming, conflict_policy="invalid")
