from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TLINKS_SRC = ROOT / "textgraphx" / "TlinksRecognizer.py"
MEANTIME_SRC = ROOT / "textgraphx" / "evaluation" / "meantime_evaluator.py"


def test_tlinks_case_queries_resolve_timexmention_to_canonical_timex():
    src = TLINKS_SRC.read_text(encoding="utf-8")

    assert "tm:TimexMention OR tm:TIMEX" in src
    assert "OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)" in src
    assert "coalesce(t_ref, CASE WHEN tm:TIMEX THEN tm ELSE NULL END) AS t" in src


def test_meantime_projection_prefers_timexmention_spans():
    src = MEANTIME_SRC.read_text(encoding="utf-8")

    assert "MATCH (tm:TimexMention)-[:REFERS_TO]->(m)" in src
    assert "[:TRIGGERS]->(:TimexMention)-[:REFERS_TO]->(m)" in src
    assert "coalesce(tm.start_tok, trig_start, span_start, m.start_tok)" in src