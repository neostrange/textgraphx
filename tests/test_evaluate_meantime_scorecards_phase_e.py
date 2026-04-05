"""Phase-E tests for CLI evaluation output scorecards and determinism fields."""

import argparse

import pytest

from textgraphx.evaluation.meantime_evaluator import EvaluationMapping
from textgraphx.tools import evaluate_meantime


def _sample_xml(doc_id: str) -> str:
    return f"""<?xml version=\"1.0\"?>
<Document doc_id=\"{doc_id}\">
  <Markables>
    <ENTITY_MENTION m_id=\"e1\" syntactic_type=\"NAM\"><token_anchor t_id=\"1\"/></ENTITY_MENTION>
    <EVENT_MENTION m_id=\"v1\" pred=\"fall\" tense=\"PAST\"><token_anchor t_id=\"2\"/></EVENT_MENTION>
    <TIMEX3 m_id=\"t1\" type=\"DATE\" value=\"2020-01-01\"><token_anchor t_id=\"3\"/></TIMEX3>
  </Markables>
  <Relations>
    <TLINK reltype=\"BEFORE\"><source m_id=\"t1\"/><target m_id=\"v1\"/></TLINK>
    <HAS_PARTICIPANT sem_role=\"Arg0\"><source m_id=\"v1\"/><target m_id=\"e1\"/></HAS_PARTICIPANT>
  </Relations>
</Document>
"""


@pytest.mark.unit
def test_evaluate_single_xml_mode_includes_scorecards(tmp_path):
    gold = tmp_path / "gold.xml"
    pred = tmp_path / "pred.xml"
    gold.write_text(_sample_xml("1"), encoding="utf-8")
    pred.write_text(_sample_xml("1"), encoding="utf-8")

    args = argparse.Namespace(
        gold=str(gold),
        gold_dir=None,
        pred_xml=str(pred),
        pred_xml_dir=None,
        pred_neo4j=False,
        doc_id=None,
        overlap_threshold=0.5,
        max_examples=5,
        analysis_mode="strict",
        f1_threshold=0.75,
        discourse_only=False,
        normalize_nominal_boundaries=True,
        gold_like_nominal_filter=False,
        nominal_profile_mode="all",
    )

    report = evaluate_meantime._evaluate_single(args, EvaluationMapping())

    assert "scorecards" in report
    assert "time_ml_compliance" in report["scorecards"]
    assert "projection_determinism" not in report


@pytest.mark.unit
def test_evaluate_batch_xml_mode_includes_scorecards(tmp_path):
    gold_dir = tmp_path / "gold"
    pred_dir = tmp_path / "pred"
    gold_dir.mkdir()
    pred_dir.mkdir()

    (gold_dir / "doc.xml").write_text(_sample_xml("1"), encoding="utf-8")
    (pred_dir / "doc.xml").write_text(_sample_xml("1"), encoding="utf-8")

    args = argparse.Namespace(
        gold=None,
        gold_dir=str(gold_dir),
        pred_xml=None,
        pred_xml_dir=str(pred_dir),
        pred_neo4j=False,
        doc_id=None,
        overlap_threshold=0.5,
        max_examples=5,
        analysis_mode="strict",
        f1_threshold=0.75,
        discourse_only=False,
        normalize_nominal_boundaries=True,
        gold_like_nominal_filter=False,
        nominal_profile_mode="all",
    )

    report = evaluate_meantime._evaluate_batch(args, EvaluationMapping())

    assert "scorecards" in report
    assert "beyond_timeml_reasoning" in report["scorecards"]
