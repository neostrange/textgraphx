"""Unit tests for TemporalPhase EventMention creation query semantics."""

from __future__ import annotations

from unittest.mock import MagicMock

from textgraphx.TemporalPhase import TemporalPhase


def _make_phase_with_graph() -> tuple[TemporalPhase, MagicMock]:
    phase = TemporalPhase.__new__(TemporalPhase)
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"mentions_created": 1}]
    phase.graph = graph
    return phase, graph


def test_create_event_mentions2_encodes_phrasal_verb_logic():
    phase, graph = _make_phase_with_graph()

    phase.create_event_mentions2("76437")

    query = graph.run.call_args[0][0]
    assert "head(collect(tok)) AS trig_tok" in query
    assert "trig_tok.pos STARTS WITH 'VB'" in query
    assert "next_tok.pos = 'RP'" in query
    assert "trigger_lemma + ' ' + toLower(trim(toString(next_tok.lemma)))" in query
    assert "em.end_tok = CASE" in query


def test_create_event_mentions2_passes_doc_id_parameter():
    phase, graph = _make_phase_with_graph()

    phase.create_event_mentions2("76437")

    params = graph.run.call_args.kwargs["parameters"]
    assert params["doc_id"] == "76437"
