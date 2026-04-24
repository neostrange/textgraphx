"""Phase-0 provenance contract tests (authority-aware metadata)."""

from unittest.mock import MagicMock

import pytest

from textgraphx.provenance import stamp_inferred_relationships
from textgraphx.reasoning.provenance import stamp_inferred_relationships as canonical_stamp_inferred_relationships


@pytest.mark.unit
def test_root_provenance_wrapper_reexports_canonical_stamper():
    assert stamp_inferred_relationships is canonical_stamp_inferred_relationships


@pytest.mark.unit
def test_stamp_inferred_relationships_sets_authority_defaults():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    count = stamp_inferred_relationships(
        graph,
        rel_type="DESCRIBES",
        confidence=0.70,
        evidence_source="event_enrichment",
        rule_id="frame_to_event",
    )

    assert count == 1
    params = graph.run.call_args[0][1]
    assert params["authority_tier"] == "secondary"
    assert params["source_kind"] == "rule"
    assert params["conflict_policy"] == "additive"


@pytest.mark.unit
def test_stamp_inferred_relationships_allows_explicit_metadata():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 2}]

    stamp_inferred_relationships(
        graph,
        rel_type="TLINK",
        confidence=0.8,
        evidence_source="tlinks_recognizer",
        rule_id="case_rules",
        authority_tier="primary",
        source_kind="service",
        conflict_policy="merge",
        extra_properties={"notes": "gated"},
    )

    params = graph.run.call_args[0][1]
    assert params["authority_tier"] == "primary"
    assert params["source_kind"] == "service"
    assert params["conflict_policy"] == "merge"
    assert params["meta_notes"] == "gated"


@pytest.mark.unit
def test_stamp_inferred_relationships_rejects_invalid_controls():
    graph = MagicMock()

    with pytest.raises(ValueError):
        stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.5,
            evidence_source="tlinks_recognizer",
            rule_id="case_rules",
            source_kind="invalid",
        )

    with pytest.raises(ValueError):
        stamp_inferred_relationships(
            graph,
            rel_type="TLINK",
            confidence=0.5,
            evidence_source="tlinks_recognizer",
            rule_id="case_rules",
            conflict_policy="invalid",
        )


@pytest.mark.regression
def test_validate_inferred_relationship_provenance_contract():
    from textgraphx.provenance import validate_inferred_relationship_provenance

    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 4}]

    result = validate_inferred_relationship_provenance(graph, rel_type="PARTICIPANT")

    assert isinstance(result, int)
    assert result == 4
