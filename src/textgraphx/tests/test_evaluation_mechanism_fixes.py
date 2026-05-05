"""Tests for the 9-issue evaluation mechanism audit fixes.

Covers the following fixes applied to meantime_evaluator.py:
- Issue 4: unmatched_gold_events populated from event strict FN count
- Issue 2: frame_fallback_event_count tracked via source_priority
- Issue 3: strict_nom_layer_filter parameter controls NOM projection
- Issue 9: TIMEX functionInDocument "NONE" injection removed
- Issues 1/5: span collapse fallback warning emitted on LOGGER.debug
- Issue 7: empty prediction warning when entity+event rows both empty
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from textgraphx.evaluation.meantime_evaluator import (
    Mention,
    NormalizedDocument,
    Relation,
    _canonicalize_timex_attrs,
    build_document_from_neo4j,
    evaluate_documents,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph(entity_rows=None, event_rows=None, timex_rows=None, resolve_id=42):
    """Build a minimal mock Neo4j graph object for projection tests."""
    graph = MagicMock()
    cursor = MagicMock()

    def _run(query, params=None):
        c = MagicMock()
        q = str(query)
        if "MATCH (m:TIMEX)" in q:
            c.data.return_value = timex_rows or []
        elif "TEvent" in q or "EventMention" in q or "Frame" in q:
            c.data.return_value = event_rows or []
        elif "AnnotatedText" in q and "CONTAINS_SENTENCE" in q:
            c.data.return_value = entity_rows or []
        elif "publicId" in q:
            c.data.return_value = [{"id": resolve_id}] if resolve_id is not None else []
        elif "TLINK" in q or "PARTICIPANT" in q:
            c.data.return_value = []
        else:
            c.data.return_value = []
        return c

    graph.run.side_effect = _run
    return graph


def _event_row(start_tok=0, end_tok=0, pred="attack", pos="VERB", source_priority=1):
    return {
        "start_tok": start_tok,
        "end_tok": end_tok,
        "pos": pos,
        "tense": "",
        "aspect": "",
        "certainty": "",
        "polarity": "",
        "time": "",
        "factuality": "",
        "pred": pred,
        "external_ref": "",
        "source_priority": source_priority,
    }


def _entity_row(start_tok=0, end_tok=1, syntactic_type="NAM", is_nominal_mention=False):
    return {
        "start_tok": start_tok,
        "end_tok": end_tok,
        "node_id": f"n{start_tok}",
        "syntactic_type": syntactic_type,
        "is_nominal_mention": is_nominal_mention,
        "eval_start_tok": start_tok,
        "eval_end_tok": end_tok,
        "ent_class": None,
        "head_token_index": end_tok,
        "head_pos": "NNP" if syntactic_type == "NAM" else "NN",
        "upos": "PROPN" if syntactic_type == "NAM" else "NOUN",
        "wn_lexname": "",
    }


# ---------------------------------------------------------------------------
# Issue 4: unmatched_gold_events
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unmatched_gold_events_populated_from_event_fn():
    """evaluate_documents must set predicted_doc.unmatched_gold_events from strict event FN."""
    gold = NormalizedDocument(doc_id="test")
    gold.event_mentions.add(Mention(kind="event", span=(5,), attrs=(("pred", "say"),)))
    gold.event_mentions.add(Mention(kind="event", span=(10,), attrs=(("pred", "attack"),)))

    predicted = NormalizedDocument(doc_id="test")
    # Only one event matches gold
    predicted.event_mentions.add(Mention(kind="event", span=(5,), attrs=(("pred", "say"),)))

    result = evaluate_documents(gold_doc=gold, predicted_doc=predicted)

    # One gold event unmatched → FN = 1
    assert predicted.unmatched_gold_events == 1
    assert result["unmatched_gold_events"] == 1


@pytest.mark.unit
def test_unmatched_gold_events_zero_when_all_match():
    """unmatched_gold_events must be 0 when predicted fully covers gold events."""
    gold = NormalizedDocument(doc_id="test")
    gold.event_mentions.add(Mention(kind="event", span=(3,), attrs=(("pred", "run"),)))

    predicted = NormalizedDocument(doc_id="test")
    predicted.event_mentions.add(Mention(kind="event", span=(3,), attrs=(("pred", "run"),)))

    result = evaluate_documents(gold_doc=gold, predicted_doc=predicted)

    assert predicted.unmatched_gold_events == 0
    assert result["unmatched_gold_events"] == 0


# ---------------------------------------------------------------------------
# Issue 2: frame_fallback_event_count (source_priority=0)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_frame_fallback_event_count_tracks_branch3():
    """frame_fallback_event_count must count events with source_priority=0 in final projection."""
    graph = _make_graph(
        event_rows=[
            _event_row(start_tok=0, end_tok=0, pred="attack", source_priority=1),
            _event_row(start_tok=5, end_tok=5, pred="fallback_event", source_priority=0),
        ],
    )
    doc = build_document_from_neo4j(graph, doc_id="42")
    assert doc.frame_fallback_event_count == 1


@pytest.mark.unit
def test_frame_fallback_event_count_zero_when_no_branch3():
    """frame_fallback_event_count must be 0 when no events come from source_priority=0."""
    graph = _make_graph(
        event_rows=[
            _event_row(start_tok=0, end_tok=0, pred="run", source_priority=2),
            _event_row(start_tok=3, end_tok=3, pred="jump", source_priority=1),
        ],
    )
    doc = build_document_from_neo4j(graph, doc_id="42")
    assert doc.frame_fallback_event_count == 0


@pytest.mark.unit
def test_frame_fallback_count_respects_deduplication():
    """When branch3 event is overridden by higher-priority entry, count should be 0."""
    # Same span with priority 0 then 1 — higher priority wins, branch3 is evicted
    graph = _make_graph(
        event_rows=[
            _event_row(start_tok=5, end_tok=5, pred="fallback", source_priority=0),
            _event_row(start_tok=5, end_tok=5, pred="attack", source_priority=1),
        ],
    )
    doc = build_document_from_neo4j(graph, doc_id="42")
    # The span (5,) should end up with priority 1, so frame_fallback_event_count=0
    assert doc.frame_fallback_event_count == 0


# ---------------------------------------------------------------------------
# Issue 3: strict_nom_layer_filter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_strict_nom_filter_excludes_non_nominal_nom_nodes():
    """When strict_nom_layer_filter=True, NOM rows without is_nominal_mention=True are excluded."""
    # Two NOM rows: one is explicit nominal mention, one is not
    entity_rows = [
        _entity_row(start_tok=0, end_tok=1, syntactic_type="NOM", is_nominal_mention=True),
        _entity_row(start_tok=5, end_tok=6, syntactic_type="NOM", is_nominal_mention=False),
    ]
    graph = _make_graph(entity_rows=entity_rows)

    doc = build_document_from_neo4j(graph, doc_id="42", strict_nom_layer_filter=True)
    # Only the explicit NominalMention row passes the filter
    assert len(doc.entity_mentions) == 1


@pytest.mark.unit
def test_strict_nom_filter_off_includes_all_nom_nodes():
    """Default (strict_nom_layer_filter=False) must not filter any NOM entities."""
    entity_rows = [
        _entity_row(start_tok=0, end_tok=1, syntactic_type="NOM", is_nominal_mention=True),
        _entity_row(start_tok=5, end_tok=6, syntactic_type="NOM", is_nominal_mention=False),
    ]
    graph = _make_graph(entity_rows=entity_rows)

    doc = build_document_from_neo4j(graph, doc_id="42", strict_nom_layer_filter=False)
    # Both NOM rows pass — default backward-compatible behaviour
    assert len(doc.entity_mentions) == 2


# ---------------------------------------------------------------------------
# Issue 9: TIMEX functionInDocument no "NONE" injection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_canonicalize_timex_attrs_no_none_injection_when_absent():
    """_canonicalize_timex_attrs must NOT add functionInDocument='NONE' when field is absent."""
    row: Dict[str, Any] = {"type": "DATE", "value": "2023-01-15"}
    attrs = dict(_canonicalize_timex_attrs(row))
    assert "functionInDocument" not in attrs


@pytest.mark.unit
def test_canonicalize_timex_attrs_includes_functionInDocument_when_present():
    """_canonicalize_timex_attrs must preserve functionInDocument when it has a real value."""
    row: Dict[str, Any] = {
        "type": "DATE",
        "value": "2023-01-15",
        "functionInDocument": "CREATION_TIME",
    }
    attrs = dict(_canonicalize_timex_attrs(row))
    assert attrs.get("functionInDocument") == "CREATION_TIME"


@pytest.mark.unit
def test_canonicalize_timex_attrs_no_none_injection_when_null():
    """_canonicalize_timex_attrs must not add functionInDocument when Neo4j returns None."""
    row: Dict[str, Any] = {"type": "TIME", "value": "T14:30", "functionInDocument": None}
    attrs = dict(_canonicalize_timex_attrs(row))
    assert "functionInDocument" not in attrs


# ---------------------------------------------------------------------------
# Issues 1/5: span collapse fallback warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_span_collapse_fallback_emits_debug_log(caplog):
    """A debug warning must be logged when headword is not found in multi-token event span."""
    # Create a graph where event has multi-token span but pred doesn't match any token
    gold_token_sequence = (
        (0, "The"), (1, "big"), (2, "company"), (3, "surprised"), (4, "everyone"),
    )
    graph = _make_graph(
        event_rows=[
            {
                "start_tok": 1,
                "end_tok": 3,
                "pos": "VERB",
                "tense": "",
                "aspect": "",
                "certainty": "",
                "polarity": "",
                "time": "",
                "factuality": "",
                "pred": "nonexistent_lemma_xyz",
                "external_ref": "",
                "source_priority": 1,
            }
        ],
    )

    with caplog.at_level(logging.DEBUG, logger="textgraphx.evaluation.meantime_evaluator"):
        build_document_from_neo4j(
            graph,
            doc_id="42",
            gold_token_sequence=gold_token_sequence,
        )

    assert any(
        "event_span_collapse_fallback" in r.message for r in caplog.records
    ), "Expected a debug log for span collapse fallback, none found"


# ---------------------------------------------------------------------------
# Issue 7: empty prediction warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_prediction_emits_warning(caplog):
    """A WARNING must be logged when entity+event rows are both empty for a resolved doc_id."""
    graph = _make_graph(entity_rows=[], event_rows=[])

    with caplog.at_level(logging.WARNING, logger="textgraphx.evaluation.meantime_evaluator"):
        doc = build_document_from_neo4j(graph, doc_id="42")

    assert not doc.entity_mentions
    assert not doc.event_mentions
    warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(
        "no entities or events" in m for m in warning_messages
    ), f"Expected empty-projection warning. Got: {warning_messages}"


# ---------------------------------------------------------------------------
# evaluate_documents return dict includes new fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evaluate_documents_returns_frame_fallback_count():
    """evaluate_documents must include frame_fallback_event_count in the returned dict."""
    gold = NormalizedDocument(doc_id="test")
    predicted = NormalizedDocument(doc_id="test")
    predicted.frame_fallback_event_count = 3

    result = evaluate_documents(gold_doc=gold, predicted_doc=predicted)
    assert result.get("frame_fallback_event_count") == 3


@pytest.mark.unit
def test_evaluate_documents_returns_unmatched_gold_events():
    """evaluate_documents must include unmatched_gold_events in the returned dict."""
    gold = NormalizedDocument(doc_id="test")
    gold.event_mentions.add(Mention(kind="event", span=(1,), attrs=(("pred", "fall"),)))
    gold.event_mentions.add(Mention(kind="event", span=(2,), attrs=(("pred", "rise"),)))

    predicted = NormalizedDocument(doc_id="test")
    # no events predicted — all 2 gold events are FN

    result = evaluate_documents(gold_doc=gold, predicted_doc=predicted)
    assert result["unmatched_gold_events"] == 2
