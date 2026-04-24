"""Regression tests for evaluate_meantime CLI helpers."""

from __future__ import annotations

import argparse
import builtins
import sys
import types

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


def test_evaluate_batch_xml_mode_does_not_import_neo4j(tmp_path, monkeypatch):
    gold_dir = tmp_path / "gold"
    pred_dir = tmp_path / "pred"
    gold_dir.mkdir()
    pred_dir.mkdir()

    (gold_dir / "doc.xml").write_text(_sample_xml("1"), encoding="utf-8")
    (pred_dir / "doc.xml").write_text(_sample_xml("1"), encoding="utf-8")

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "textgraphx.database.client":
            raise AssertionError("neo4j client should not be imported for --pred-xml-dir mode")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

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
    )

    report = evaluate_meantime._evaluate_batch(args, EvaluationMapping())

    assert report["mode"] == "batch"
    assert report["documents_evaluated"] == 1
    assert report["evaluation_scope"] == {
        "discourse_only": False,
        "entity_filter": "none",
        "event_filter": "none",
        "relation_scope": ["has_participant", "tlink"],
        "nominal_profile_mode": "all",
        "gold_like_nominal_filter": False,
        "nominal_precision_filters": False,
    }
    assert report["aggregate"]["micro"]["strict"]["entity"]["f1"] == 1.0


def test_evaluate_batch_reports_skipped_prediction_files(tmp_path):
    gold_dir = tmp_path / "gold"
    pred_dir = tmp_path / "pred"
    gold_dir.mkdir()
    pred_dir.mkdir()

    (gold_dir / "doc1.xml").write_text(_sample_xml("1"), encoding="utf-8")
    (gold_dir / "doc2.xml").write_text(_sample_xml("2"), encoding="utf-8")
    (pred_dir / "doc1.xml").write_text(_sample_xml("1"), encoding="utf-8")

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
    )

    report = evaluate_meantime._evaluate_batch(args, EvaluationMapping())

    assert report["documents_evaluated"] == 1
    assert report["skipped_prediction_files"] == ["doc2.xml"]


def test_evaluate_single_includes_evaluation_scope_default_false(tmp_path):
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
    )

    report = evaluate_meantime._evaluate_single(args, EvaluationMapping())

    assert report["evaluation_scope"] == {
        "discourse_only": False,
        "entity_filter": "none",
        "event_filter": "none",
        "relation_scope": ["has_participant", "tlink"],
        "nominal_profile_mode": "all",
        "gold_like_nominal_filter": False,
        "nominal_precision_filters": False,
    }


def test_evaluate_single_includes_evaluation_scope_discourse_true(tmp_path):
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
        discourse_only=True,
    )

    report = evaluate_meantime._evaluate_single(args, EvaluationMapping())

    assert report["evaluation_scope"] == {
        "discourse_only": True,
        "entity_filter": "DiscourseEntity label",
        "event_filter": "none",
        "relation_scope": ["has_participant", "tlink"],
        "nominal_profile_mode": "all",
        "gold_like_nominal_filter": False,
        "nominal_precision_filters": False,
    }


def test_build_operator_summary_for_batch_report():
    report = {
        "mode": "batch",
        "documents_evaluated": 7,
        "skipped_prediction_files": ["a.xml", "b.xml"],
    }
    summary = evaluate_meantime._build_operator_summary(report)
    assert summary == "Batch evaluation summary: evaluated=7, skipped_missing_predictions=2"


def test_build_operator_summary_non_batch_is_none():
    report = {"mode": "single", "doc_id": "123"}
    assert evaluate_meantime._build_operator_summary(report) is None


def test_single_report_top_level_schema_contains_evaluation_scope(tmp_path):
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
    )

    report = evaluate_meantime._evaluate_single(args, EvaluationMapping())

    assert set(report.keys()) >= {
        "doc_id",
        "counts",
        "strict",
        "relaxed",
        "diagnostics",
        "evaluation_scope",
    }


def test_batch_report_top_level_schema_contains_evaluation_scope(tmp_path):
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
    )

    report = evaluate_meantime._evaluate_batch(args, EvaluationMapping())

    assert set(report.keys()) >= {
        "mode",
        "documents_evaluated",
        "skipped_prediction_files",
        "evaluation_scope",
        "aggregate",
        "diagnostics",
        "reports",
    }


def test_evaluate_batch_neo4j_includes_nominal_scope_fields(tmp_path, monkeypatch):
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "doc.xml").write_text(_sample_xml("1"), encoding="utf-8")

    class _FakeGraph:
        def close(self):
            return None

    fake_mod = types.SimpleNamespace(make_graph_from_config=lambda: _FakeGraph())
    monkeypatch.setitem(sys.modules, "textgraphx.database.client", fake_mod)

    captured = {}

    def _fake_build_document_from_neo4j(**kwargs):
        captured.update(kwargs)
        return evaluate_meantime.parse_meantime_xml(str(gold_dir / "doc.xml"))

    monkeypatch.setattr(evaluate_meantime, "build_document_from_neo4j", _fake_build_document_from_neo4j)

    args = argparse.Namespace(
        gold=None,
        gold_dir=str(gold_dir),
        pred_xml=None,
        pred_xml_dir=None,
        pred_neo4j=True,
        doc_id=None,
        overlap_threshold=0.5,
        max_examples=5,
        analysis_mode="strict",
        f1_threshold=0.75,
        discourse_only=True,
        normalize_nominal_boundaries=True,
        gold_like_nominal_filter=True,
        nominal_profile_mode="candidate-gold",
    )

    report = evaluate_meantime._evaluate_batch(args, EvaluationMapping())

    assert captured.get("nominal_profile_mode") == "candidate-gold"
    assert report["evaluation_scope"] == {
        "discourse_only": True,
        "entity_filter": "DiscourseEntity label",
        "event_filter": "none",
        "relation_scope": ["has_participant", "tlink"],
        "nominal_profile_mode": "candidate-gold",
        "gold_like_nominal_filter": True,
        "nominal_precision_filters": False,
    }
