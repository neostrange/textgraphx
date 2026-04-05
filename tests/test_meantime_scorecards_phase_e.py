"""Phase-E tests for evaluator scorecards and projection determinism helpers."""

import pytest


@pytest.mark.unit
def test_build_dual_scorecards_from_aggregate_has_expected_keys():
    from textgraphx.evaluation.meantime_evaluator import build_dual_scorecards_from_aggregate

    aggregate = {
        "micro": {
            "strict": {
                "event": {"f1": 0.6},
                "timex": {"f1": 0.8},
                "relation": {"f1": 0.5},
            },
            "relaxed": {
                "event": {"f1": 0.7},
                "timex": {"f1": 0.85},
                "relation": {"f1": 0.65},
            },
        }
    }

    out = build_dual_scorecards_from_aggregate(aggregate)

    assert "time_ml_compliance" in out
    assert "beyond_timeml_reasoning" in out
    assert out["time_ml_compliance"]["composite"] > 0.0
    assert out["beyond_timeml_reasoning"]["relation_gain"] >= 0.0


@pytest.mark.unit
def test_check_projection_determinism_detects_non_deterministic_projection(monkeypatch):
    from textgraphx.evaluation import meantime_evaluator as me
    from textgraphx.evaluation.meantime_evaluator import Mention, NormalizedDocument

    calls = {"n": 0}

    def fake_build_document_from_neo4j(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return NormalizedDocument(doc_id="1", event_mentions={Mention(kind="event", span=(1,), attrs=())})
        return NormalizedDocument(doc_id="1", event_mentions={Mention(kind="event", span=(2,), attrs=())})

    monkeypatch.setattr(me, "build_document_from_neo4j", fake_build_document_from_neo4j)

    out = me.check_projection_determinism(graph=object(), doc_id="1", runs=2)

    assert out["deterministic"] is False
    assert out["mismatch_runs"] == [1]
