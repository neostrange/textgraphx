from pathlib import Path


def test_meantime_evaluator_accepts_and_projects_factuality():
    src = Path(__file__).resolve().parents[1] / "evaluation" / "meantime_evaluator.py"
    text = src.read_text(encoding="utf-8")

    assert '"factuality"' in text
    assert "m.factuality AS factuality" in text
    assert "attrs_map[\"factuality\"]" in text
