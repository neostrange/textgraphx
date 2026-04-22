from pathlib import Path


def test_meantime_parser_accepts_clink_and_slink_tags():
    src = Path(__file__).resolve().parents[1] / "evaluation" / "meantime_evaluator.py"
    text = src.read_text(encoding="utf-8")

    assert '"CLINK"' in text
    assert '"SLINK"' in text
    assert 'if rel.tag not in {"TLINK", "GLINK", "CLINK", "SLINK", "HAS_PARTICIPANT"}' in text


def test_meantime_neo4j_projection_queries_clink_and_slink():
    src = Path(__file__).resolve().parents[1] / "evaluation" / "meantime_evaluator.py"
    text = src.read_text(encoding="utf-8")

    assert 'MATCH (a)-[r:CLINK|SLINK]->(b)' in text
    assert 'RETURN type(r) AS rel_kind' in text
