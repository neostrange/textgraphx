"""Tests for MEANTIME-oriented evaluator."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from textgraphx.evaluation.meantime_evaluator import (
    _canonicalize_event_attrs,
    _canonicalize_timex_attrs,
    EvaluationMapping,
    Mention,
    NormalizedDocument,
    Relation,
    aggregate_reports,
    build_document_from_neo4j,
    build_dataset_diagnostics,
    build_document_diagnostics,
    evaluate_documents,
    flatten_aggregate_rows_for_csv,
    flatten_report_rows_for_csv,
    parse_meantime_xml,
    render_markdown_report,
    score_mention_layer,
    score_relation_layer,
)


def _write_tmp_xml(content: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as f:
        f.write(content)
        return f.name


def test_parse_meantime_xml_extracts_core_layers():
    xml = """<?xml version=\"1.0\"?>
<Document doc_id=\"1\">
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
    path = _write_tmp_xml(xml)
    doc = parse_meantime_xml(path)

    assert doc.doc_id == "1"
    assert len(doc.entity_mentions) == 1
    assert len(doc.event_mentions) == 1
    assert len(doc.timex_mentions) == 1
    assert len(doc.relations) == 2


def test_relaxed_span_matching_can_recover_boundary_drift():
    gold = {
        Mention(kind="entity", span=(1, 2), attrs=(("syntactic_type", "NAM"),)),
    }
    pred = {
        Mention(kind="entity", span=(1, 2, 3), attrs=(("syntactic_type", "NAM"),)),
    }

    strict = score_mention_layer(gold, pred, mode="strict", overlap_threshold=0.5)
    relaxed = score_mention_layer(gold, pred, mode="relaxed", overlap_threshold=0.5)

    assert strict["tp"] == 0
    assert relaxed["tp"] == 1
    assert relaxed["f1"] == 1.0


def test_end_to_end_self_comparison_on_real_sample_is_perfect():
    root = Path(__file__).resolve().parent.parent
    sample = root / "datastore" / "annotated" / "76437_Markets_dragged_down_by_credit_crisis.xml"

    gold_doc = parse_meantime_xml(str(sample))
    pred_doc = parse_meantime_xml(str(sample))

    report = evaluate_documents(gold_doc, pred_doc)

    assert report["strict"]["entity"]["f1"] == 1.0
    assert report["strict"]["event"]["f1"] == 1.0
    assert report["strict"]["timex"]["f1"] == 1.0


def test_mention_error_buckets_are_reported():
    gold = {
        Mention(kind="entity", span=(10, 11), attrs=(("syntactic_type", "NAM"),)),
        Mention(kind="entity", span=(20,), attrs=(("syntactic_type", "NOM"),)),
    }
    pred = {
        Mention(kind="entity", span=(10, 11), attrs=(("syntactic_type", "NOM"),)),
        Mention(kind="entity", span=(20, 21), attrs=(("syntactic_type", "NOM"),)),
        Mention(kind="entity", span=(99,), attrs=(("syntactic_type", "NAM"),)),
    }

    strict = score_mention_layer(gold, pred, mode="strict", overlap_threshold=0.5)
    assert "errors" in strict
    assert strict["errors"]["type_mismatch"] >= 1
    assert strict["errors"]["boundary_mismatch"] >= 1
    assert strict["errors"]["spurious"] >= 1


def test_mapping_can_ignore_event_attributes_in_strict_mode():
    gold_doc = NormalizedDocument(
        doc_id="d1",
        event_mentions={Mention(kind="event", span=(5,), attrs=(("tense", "PAST"), ("pred", "fall")))},
    )
    pred_doc = NormalizedDocument(
        doc_id="d1",
        event_mentions={Mention(kind="event", span=(5,), attrs=(("tense", "PRESENT"), ("pred", "fall")))},
    )

    default_report = evaluate_documents(gold_doc, pred_doc)
    assert default_report["strict"]["event"]["tp"] == 0

    mapped = EvaluationMapping(
        mention_attr_keys={"entity": ("syntactic_type",), "event": ("pred",), "timex": ("type", "value", "functionInDocument")},
        relation_attr_keys={"tlink": ("reltype",), "has_participant": ("sem_role",)},
    )
    mapped_report = evaluate_documents(gold_doc, pred_doc, mapping=mapped)
    assert mapped_report["strict"]["event"]["tp"] == 1


def test_aggregate_reports_micro_macro_shape():
    reports = [
        {
            "strict": {
                "entity": {"tp": 2, "fp": 1, "fn": 1, "precision": 2 / 3, "recall": 2 / 3, "f1": 2 / 3},
                "event": {"tp": 1, "fp": 0, "fn": 1, "precision": 1.0, "recall": 0.5, "f1": 2 / 3},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
                "relation": {"tp": 0, "fp": 1, "fn": 1, "precision": 0.0, "recall": 0.0, "f1": 0.0},
            },
            "relaxed": {
                "entity": {"tp": 3, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
                "event": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
                "relation": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
            },
        }
    ]

    agg = aggregate_reports(reports)
    assert agg["documents"] == 1
    assert agg["micro"]["strict"]["entity"]["tp"] == 2
    assert agg["macro"]["strict"]["timex"]["f1"] == 1.0


def test_document_diagnostics_contains_suggestions_for_weak_layers():
    report = {
        "doc_id": "x1",
        "strict": {
            "entity": {"tp": 1, "fp": 2, "fn": 3, "precision": 0.333, "recall": 0.25, "f1": 0.286, "errors": {"boundary_mismatch": 1, "type_mismatch": 1, "missing": 3, "spurious": 2}},
            "event": {"tp": 5, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
            "timex": {"tp": 1, "fp": 1, "fn": 1, "precision": 0.5, "recall": 0.5, "f1": 0.5, "errors": {"missing": 1, "spurious": 1}},
            "relation": {"tp": 0, "fp": 2, "fn": 2, "precision": 0.0, "recall": 0.0, "f1": 0.0, "errors": {"missing": 2, "spurious": 2}},
        },
    }
    diag = build_document_diagnostics(report, mode="strict", f1_threshold=0.75)
    assert "entity" in diag["weak_layers"]
    assert len(diag["suggestions"]) > 0


def test_dataset_diagnostics_exposes_hotspots_and_issue_totals():
    reports = [
        {
            "doc_id": "d1",
            "strict": {
                "entity": {"tp": 1, "fp": 2, "fn": 2, "precision": 0.33, "recall": 0.33, "f1": 0.33, "errors": {"missing": 2, "spurious": 2}},
                "event": {"tp": 2, "fp": 0, "fn": 1, "precision": 1.0, "recall": 0.66, "f1": 0.8, "errors": {"missing": 1}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 0, "fp": 1, "fn": 2, "precision": 0.0, "recall": 0.0, "f1": 0.0, "errors": {"missing": 2, "spurious": 1}},
            },
            "relaxed": {
                "entity": {"tp": 2, "fp": 1, "fn": 1, "precision": 0.66, "recall": 0.66, "f1": 0.66, "errors": {"missing": 1, "spurious": 1}},
                "event": {"tp": 2, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 1, "fp": 0, "fn": 1, "precision": 1.0, "recall": 0.5, "f1": 0.66, "errors": {"missing": 1}},
            },
        }
    ]
    agg = aggregate_reports(reports)
    dataset_diag = build_dataset_diagnostics(reports, agg, mode="strict", f1_threshold=0.75)
    assert len(dataset_diag["hotspot_documents"]) >= 1
    assert "entity" in dataset_diag["issue_totals"]


def test_csv_flatteners_produce_rows():
    reports = [
        {
            "doc_id": "d1",
            "strict": {
                "entity": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "event": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
            },
            "relaxed": {
                "entity": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "event": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
            },
        }
    ]
    rows = flatten_report_rows_for_csv(reports, mode="strict")
    assert len(rows) == 4
    agg_rows = flatten_aggregate_rows_for_csv(aggregate_reports(reports))
    assert len(agg_rows) > 0


def test_render_markdown_report_contains_key_sections():
    reports = [
        {
            "doc_id": "d1",
            "strict": {
                "entity": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "event": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
            },
            "relaxed": {
                "entity": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "event": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "timex": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
                "relation": {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "errors": {}},
            },
        }
    ]
    agg = aggregate_reports(reports)
    diag = build_dataset_diagnostics(reports, agg, mode="strict", f1_threshold=0.9)
    report = {
        "mode": "batch",
        "documents_evaluated": 1,
        "aggregate": agg,
        "diagnostics": diag,
        "reports": reports,
    }

    md = render_markdown_report(report)
    assert "# Evaluation Report" in md
    assert "## Aggregate Metrics" in md
    assert "## Per-Document Diagnostics" in md


def test_render_markdown_report_renders_batch_determinism_correctly():
    """Batch reports use 'all_stable'; markdown must read that, not the per-doc 'deterministic' field."""
    report = {
        "mode": "batch",
        "documents_evaluated": 2,
        "aggregate": {},
        "diagnostics": {},
        "reports": [],
        "projection_determinism": {
            "all_stable": True,
            "documents_checked": 2,
            "stable_documents": 2,
            "unstable_documents": 0,
            "runs": 2,
            "by_doc": {
                "doc1": {"deterministic": True, "runs": 2, "mismatch_runs": []},
                "doc2": {"deterministic": True, "runs": 2, "mismatch_runs": []},
            },
        },
    }
    md = render_markdown_report(report)
    assert "## Projection Determinism" in md
    assert "- Deterministic: True" in md
    assert "- Documents: 2/2 stable" in md
    assert "- Runs: 2" in md
    assert "Unstable docs:" not in md


def test_render_markdown_report_renders_batch_determinism_with_unstable_docs():
    report = {
        "mode": "batch",
        "documents_evaluated": 2,
        "aggregate": {},
        "diagnostics": {},
        "reports": [],
        "projection_determinism": {
            "all_stable": False,
            "documents_checked": 2,
            "stable_documents": 1,
            "unstable_documents": 1,
            "runs": 3,
            "by_doc": {
                "stable_doc": {"deterministic": True, "runs": 3, "mismatch_runs": []},
                "flaky_doc": {"deterministic": False, "runs": 3, "mismatch_runs": [1, 2]},
            },
        },
    }
    md = render_markdown_report(report)
    assert "- Deterministic: False" in md
    assert "- Documents: 1/2 stable, 1 unstable" in md
    assert "- Unstable docs: flaky_doc" in md


def test_render_markdown_report_renders_singledoc_determinism():
    """Single-doc reports use the 'deterministic' field; preserve legacy rendering."""
    report = {
        "mode": "single",
        "documents_evaluated": 1,
        "aggregate": {},
        "diagnostics": {},
        "reports": [],
        "projection_determinism": {
            "deterministic": True,
            "runs": 2,
            "mismatch_runs": [],
        },
    }
    md = render_markdown_report(report)
    assert "- Deterministic: True" in md
    assert "- Runs: 2" in md
    assert "- Mismatch runs: none" in md


def test_relation_error_bucket_detects_type_mismatch():
    gold = {
        Relation(
            kind="tlink",
            source_kind="event",
            source_span=(10,),
            target_kind="timex",
            target_span=(20,),
            attrs=(("reltype", "BEFORE"),),
        )
    }
    pred = {
        Relation(
            kind="tlink",
            source_kind="event",
            source_span=(10,),
            target_kind="timex",
            target_span=(20,),
            attrs=(("reltype", "AFTER"),),
        )
    }

    out = score_relation_layer(gold, pred, mode="strict")
    assert out["errors"]["type_mismatch"] == 1
    assert out["errors"]["missing"] == 0
    assert out["errors"]["spurious"] == 0


def test_relation_error_bucket_detects_endpoint_mismatch():
    gold = {
        Relation(
            kind="tlink",
            source_kind="event",
            source_span=(10, 11),
            target_kind="timex",
            target_span=(20, 21),
            attrs=(("reltype", "BEFORE"),),
        )
    }
    pred = {
        Relation(
            kind="tlink",
            source_kind="event",
            source_span=(11, 12),
            target_kind="timex",
            target_span=(21, 22),
            attrs=(("reltype", "BEFORE"),),
        )
    }

    out = score_relation_layer(gold, pred, mode="strict")
    assert out["errors"]["endpoint_mismatch"] == 1
    assert out["errors"]["missing"] == 0
    assert out["errors"]["spurious"] == 0


def test_relation_scoring_uses_kind_specific_attr_keys_for_clink_and_slink():
    gold = {
        Relation(
            kind="clink",
            source_kind="event",
            source_span=(10,),
            target_kind="event",
            target_span=(20,),
            attrs=(("source", "srl_argm_cau"),),
        ),
        Relation(
            kind="slink",
            source_kind="event",
            source_span=(30,),
            target_kind="event",
            target_span=(40,),
            attrs=(("source", "reported_speech_lexical"),),
        ),
    }
    pred = {
        Relation(
            kind="clink",
            source_kind="event",
            source_span=(10,),
            target_kind="event",
            target_span=(20,),
            attrs=(("source", "different_rule"),),
        ),
        Relation(
            kind="slink",
            source_kind="event",
            source_span=(30,),
            target_kind="event",
            target_span=(40,),
            attrs=(("source", "different_rule"),),
        ),
    }

    out = score_relation_layer(
        gold,
        pred,
        mode="strict",
        attr_keys={"clink": ("source",), "slink": ("source",)},
    )
    assert out["tp"] == 0
    assert out["errors"]["type_mismatch"] == 2


def test_relation_scoring_uses_kind_specific_attr_keys_for_participant_roles():
    gold = {
        Relation(
            kind="has_participant",
            source_kind="event",
            source_span=(10,),
            target_kind="entity",
            target_span=(20,),
            attrs=(("sem_role", "Arg0"),),
        )
    }
    pred = {
        Relation(
            kind="has_participant",
            source_kind="event",
            source_span=(10,),
            target_kind="entity",
            target_span=(20,),
            attrs=(("sem_role", "Arg1"),),
        )
    }

    out = score_relation_layer(
        gold,
        pred,
        mode="strict",
        attr_keys={"has_participant": ("sem_role",)},
    )
    assert out["tp"] == 0
    assert out["errors"]["type_mismatch"] == 1


def test_relaxed_relation_scoring_canonicalizes_tlink_direction_and_reltype():
    """Relaxed matching should canonicalize TLINK orientation the same way as strict.

    Gold uses TIMEX->EVENT BEFORE while prediction uses EVENT->TIMEX AFTER,
    which are semantically equivalent under TLINK inversion rules.
    """
    gold = {
        Relation(
            kind="tlink",
            source_kind="timex",
            source_span=(30,),
            target_kind="event",
            target_span=(20,),
            attrs=(("reltype", "BEFORE"),),
        )
    }
    pred = {
        Relation(
            kind="tlink",
            source_kind="event",
            source_span=(20,),
            target_kind="timex",
            target_span=(30,),
            attrs=(("reltype", "AFTER"),),
        )
    }

    strict = score_relation_layer(gold, pred, mode="strict")
    relaxed = score_relation_layer(gold, pred, mode="relaxed")

    assert strict["tp"] == 1
    assert relaxed["tp"] == 1
    assert relaxed["fp"] == 0
    assert relaxed["fn"] == 0


def test_canonicalize_event_attrs_defaults_meantime_fields_for_verbal_events():
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "VBD",
                "tense": "PAST",
                "aspect": "NONE",
                "pred": "Fall",
            }
        )
    )

    assert attrs == {
        "aspect": "NONE",
        "certainty": "CERTAIN",
        "polarity": "POS",
        "pos": "VERB",
        "pred": "fall",
        "tense": "PAST",
        "time": "NON_FUTURE",
    }


def test_canonicalize_event_attrs_omits_none_tense_aspect_for_noun_events():
    attrs = dict(
        _canonicalize_event_attrs(
            {
                "pos": "NN",
                "tense": "NONE",
                "aspect": "NONE",
                "pred": "Crisis",
            }
        )
    )

    assert attrs == {
        "certainty": "CERTAIN",
        "polarity": "POS",
        "pos": "NOUN",
        "pred": "crisis",
        "time": "NON_FUTURE",
    }


def test_canonicalize_timex_attrs_keeps_interval_anchoring_fields_when_present():
    attrs = dict(
        _canonicalize_timex_attrs(
            {
                "type": "DATE",
                "value": "20200101",
                "functionInDocument": "NONE",
                "anchorTimeID": "t0",
                "beginPoint": "t0",
                "endPoint": "t2",
            }
        )
    )

    assert attrs == {
        "anchorTimeID": "t0",
        "beginPoint": "t0",
        "endPoint": "t2",
        "functionInDocument": "NONE",
        "type": "DATE",
        "value": "2020-01-01",
    }


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows


class _FakeGraph:
    def run(self, query, params=None):
        params = params or {}
        compact = " ".join(query.split())
        if "RETURN a.id AS id" in compact:
            return _FakeResult([{"id": 1}])
        if "IN_MENTION|PARTICIPATES_IN]->(m)" in compact and "syntactic_type" in compact:
            return _FakeResult([
                {"start_tok": 10, "end_tok": 11, "syntactic_type": "NAM"},
            ])
        if "CALL {" in compact and "EventMention" in compact and "PARTICIPANT" not in compact:
            return _FakeResult([
                {
                    "start_tok": 20,
                    "end_tok": 20,
                    "pos": "VBD",
                    "tense": "PAST",
                    "aspect": "NONE",
                    "certainty": "CERTAIN",
                    "polarity": "POS",
                    "time": "NON_FUTURE",
                    "pred": "fall",
                }
            ])
        if "MATCH (m:TIMEX)" in compact:
            return _FakeResult([
                {
                    "start_tok": 30,
                    "end_tok": 31,
                    "type": "DATE",
                    "value": "2007-08-10",
                    "functionInDocument": "NONE",
                    "anchorTimeID": "t0",
                    "beginPoint": "t0",
                    "endPoint": "t2",
                }
            ])
        if "MATCH (a)-[r:TLINK]-(b)" in compact or "MATCH (a)-[r:TLINK]->(b)" in compact:
            return _FakeResult([
                {
                    "source_labels": ["TEvent"],
                    "a_start": 20,
                    "a_end": 20,
                    "target_labels": ["TIMEX"],
                    "b_start": 30,
                    "b_end": 31,
                    "reltype": "BEFORE",
                }
            ])
        if "MATCH (a)-[r:GLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:CLINK|SLINK]->(b)" in compact:
            return _FakeResult([
                {
                    "rel_kind": "CLINK",
                    "source_labels": ["TEvent"],
                    "a_start": 20,
                    "a_end": 20,
                    "target_labels": ["TEvent"],
                    "b_start": 21,
                    "b_end": 21,
                    "reltype": "CAUSES",
                    "source": "srl_argm_cau",
                },
                {
                    "rel_kind": "SLINK",
                    "source_labels": ["TEvent"],
                    "a_start": 20,
                    "a_end": 20,
                    "target_labels": ["TEvent"],
                    "b_start": 22,
                    "b_end": 22,
                    "reltype": "EPISTEMIC",
                    "source": "reported_speech_lexical",
                },
            ])
        if "MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)" in compact:
            return _FakeResult([
                {
                    "src_start": 10,
                    "src_end": 11,
                    "evt_start": 20,
                    "evt_end": 20,
                    "sem_role": "Arg0",
                    "source_labels": ["NamedEntity"],
                }
            ])
        raise AssertionError(f"Unexpected query: {compact}")


class _FakeGraphWithProjectionEdgeCases:
    def run(self, query, params=None):
        compact = " ".join(query.split())
        if "RETURN a.id AS id" in compact:
            return _FakeResult([{"id": 1}])
        if "IN_MENTION|PARTICIPATES_IN]->(m)" in compact and "syntactic_type" in compact:
            return _FakeResult([])
        if "CALL {" in compact and "EventMention" in compact and "PARTICIPANT" not in compact:
            # Same span from EventMention + TEvent fallback, but with different attrs.
            return _FakeResult(
                [
                    {
                        "start_tok": 20,
                        "end_tok": 20,
                        "pos": "VBD",
                        "tense": "PAST",
                        "aspect": "NONE",
                        "certainty": "CERTAIN",
                        "polarity": "POS",
                        "time": "NON_FUTURE",
                        "pred": "fall",
                        "source_priority": 2,
                    },
                    {
                        "start_tok": 20,
                        "end_tok": 20,
                        "pos": "VB",
                        "tense": "PRESENT",
                        "aspect": "NONE",
                        "certainty": "CERTAIN",
                        "polarity": "POS",
                        "time": "NON_FUTURE",
                        "pred": "drop",
                        "source_priority": 1,
                    },
                ]
            )
        if "MATCH (m:TIMEX)" in compact:
            # Simulate TIMEX resolved via start_tok/end_tok fallback path.
            return _FakeResult(
                [
                    {
                        "start_tok": 30,
                        "end_tok": 31,
                        "type": "DATE",
                        "value": "2007-08-10",
                        "functionInDocument": "NONE",
                    }
                ]
            )
        if "MATCH (a)-[r:TLINK]-(b)" in compact or "MATCH (a)-[r:TLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:GLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:CLINK|SLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)" in compact:
            return _FakeResult([])
        raise AssertionError(f"Unexpected query: {compact}")


class _FakeGraphDiscourseOnlyQueryShape:
    def run(self, query, params=None):
        compact = " ".join(query.split())
        if "RETURN a.id AS id" in compact:
            return _FakeResult([{"id": 1}])
        if "IN_MENTION|PARTICIPATES_IN]->(m)" in compact and "syntactic_type" in compact:
            if "AND m:DiscourseEntity" not in compact:
                raise AssertionError("Expected entity query to include DiscourseEntity clause in discourse-only mode")
            return _FakeResult([
                {"start_tok": 10, "end_tok": 10, "syntactic_type": "NAM"},
            ])
        if "CALL {" in compact and "EventMention" in compact and "PARTICIPANT" not in compact:
            if "EVENT_PARTICIPANT|PARTICIPANT" in compact:
                raise AssertionError("Event projection must remain unchanged in discourse-only mode")
            return _FakeResult([
                {
                    "start_tok": 20,
                    "end_tok": 20,
                    "pos": "VBD",
                    "tense": "PAST",
                    "aspect": "NONE",
                    "certainty": "CERTAIN",
                    "polarity": "POS",
                    "time": "NON_FUTURE",
                    "pred": "fall",
                }
            ])
        if "MATCH (m:TIMEX)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:TLINK]-(b)" in compact or "MATCH (a)-[r:TLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:GLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:CLINK|SLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)" in compact:
            return _FakeResult([])
        raise AssertionError(f"Unexpected query: {compact}")


class _FakeGraphAuxiliaryEventFiltering:
    def run(self, query, params=None):
        compact = " ".join(query.split())
        if "RETURN a.id AS id" in compact:
            return _FakeResult([{"id": 1}])
        if "IN_MENTION|PARTICIPATES_IN]->(m)" in compact and "syntactic_type" in compact:
            return _FakeResult([])
        if "CALL {" in compact and "EventMention" in compact and "PARTICIPANT" not in compact:
            return _FakeResult([
                {
                    "start_tok": 20,
                    "end_tok": 20,
                    "pos": "MD",
                    "tense": "PRESENT",
                    "aspect": "NONE",
                    "certainty": "CERTAIN",
                    "polarity": "POS",
                    "time": "FUTURE",
                    "pred": "will",
                    "source_priority": 2,
                }
            ])
        if "MATCH (m:TIMEX)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:TLINK]-(b)" in compact or "MATCH (a)-[r:TLINK]->(b)" in compact:
            return _FakeResult([
                {
                    "source_labels": ["EventMention"],
                    "a_start": 20,
                    "a_end": 20,
                    "target_labels": ["TIMEX"],
                    "b_start": 30,
                    "b_end": 30,
                    "reltype": "BEFORE",
                }
            ])
        if "MATCH (a)-[r:GLINK]->(b)" in compact:
            return _FakeResult([])
        if "MATCH (a)-[r:CLINK|SLINK]->(b)" in compact:
            return _FakeResult([
                {
                    "rel_kind": "CLINK",
                    "source_labels": ["EventMention"],
                    "a_start": 20,
                    "a_end": 20,
                    "target_labels": ["EventMention"],
                    "b_start": 20,
                    "b_end": 20,
                    "reltype": "CAUSES",
                    "source": "rule",
                }
            ])
        if "MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)" in compact:
            return _FakeResult([
                {
                    "src_start": 10,
                    "src_end": 10,
                    "evt_start": 20,
                    "evt_end": 20,
                    "sem_role": "Arg0",
                    "source_labels": ["EntityMention"],
                }
            ])
        raise AssertionError(f"Unexpected query: {compact}")


def test_build_document_from_neo4j_resolves_public_id_and_projects_relations():
    doc = build_document_from_neo4j(_FakeGraph(), "76437")

    assert doc.doc_id == "76437"
    assert Mention(kind="entity", span=(10, 11), attrs=(("syntactic_type", "NAM"),)) in doc.entity_mentions
    assert Mention(
        kind="event",
        span=(20,),
        attrs=(
            ("aspect", "NONE"),
            ("certainty", "CERTAIN"),
            ("polarity", "POS"),
            ("pos", "VERB"),
            ("pred", "fall"),
            ("tense", "PAST"),
            ("time", "NON_FUTURE"),
        ),
    ) in doc.event_mentions
    assert Mention(
        kind="timex",
        span=(30, 31),
        attrs=(
            ("anchorTimeID", "t0"),
            ("beginPoint", "t0"),
            ("endPoint", "t2"),
            ("functionInDocument", "NONE"),
            ("type", "DATE"),
            ("value", "2007-08-10"),
        ),
    ) in doc.timex_mentions
    assert len(doc.relations) == 4
    assert any(r.kind == "clink" and dict(r.attrs).get("source") == "srl_argm_cau" for r in doc.relations)
    assert any(r.kind == "slink" and dict(r.attrs).get("source") == "reported_speech_lexical" for r in doc.relations)


def test_build_document_from_neo4j_deduplicates_events_by_span_preferring_mentions():
    doc = build_document_from_neo4j(_FakeGraphWithProjectionEdgeCases(), "76437")

    assert len(doc.event_mentions) == 1
    assert Mention(
        kind="event",
        span=(20,),
        attrs=(
            ("aspect", "NONE"),
            ("certainty", "CERTAIN"),
            ("polarity", "POS"),
            ("pos", "VERB"),
            ("pred", "fall"),
            ("tense", "PAST"),
            ("time", "NON_FUTURE"),
        ),
    ) in doc.event_mentions


def test_build_document_from_neo4j_projects_timex_with_fallback_span_tokens():
    doc = build_document_from_neo4j(_FakeGraphWithProjectionEdgeCases(), "76437")

    assert Mention(
        kind="timex",
        span=(30, 31),
        attrs=(
            ("functionInDocument", "NONE"),
            ("type", "DATE"),
            ("value", "2007-08-10"),
        ),
    ) in doc.timex_mentions


def test_build_document_from_neo4j_discourse_only_filters_entities_only():
    doc = build_document_from_neo4j(_FakeGraphDiscourseOnlyQueryShape(), "76437", discourse_only=True)

    assert Mention(kind="entity", span=(10,), attrs=(("syntactic_type", "NAM"),)) in doc.entity_mentions
    assert Mention(
        kind="event",
        span=(20,),
        attrs=(
            ("aspect", "NONE"),
            ("certainty", "CERTAIN"),
            ("polarity", "POS"),
            ("pos", "VERB"),
            ("pred", "fall"),
            ("tense", "PAST"),
            ("time", "NON_FUTURE"),
        ),
    ) in doc.event_mentions


def test_build_document_from_neo4j_filters_auxiliary_events_and_attached_relations():
    doc = build_document_from_neo4j(_FakeGraphAuxiliaryEventFiltering(), "76437")

    assert doc.event_mentions == set()
    assert doc.relations == set()


def test_parse_meantime_xml_reads_event_external_ref_and_glink():
    xml = """
    <Document doc_id="1">
      <Markables>
        <EVENT_MENTION m_id="v1" pred="fall" tense="PAST" external_ref="ev:42"><token_anchor t_id="2"/></EVENT_MENTION>
        <EVENT_MENTION m_id="v2" pred="recover" tense="PAST"><token_anchor t_id="3"/></EVENT_MENTION>
      </Markables>
      <Relations>
        <GLINK reltype="CONDITIONAL"><source m_id="v1"/><target m_id="v2"/></GLINK>
      </Relations>
    </Document>
    """
    path = _write_tmp_xml(xml)
    doc = parse_meantime_xml(path)

    assert Mention(kind="event", span=(2,), attrs=(("external_ref", "ev:42"), ("pred", "fall"), ("tense", "PAST"))) in doc.event_mentions
    assert any(r.kind == "glink" and dict(r.attrs).get("reltype") == "CONDITIONAL" for r in doc.relations)


def test_parse_meantime_xml_reads_clink_and_slink_relations():
        xml = """
        <Document doc_id="1">
            <Markables>
                <EVENT_MENTION m_id="v1" pred="fall" tense="PAST"><token_anchor t_id="2"/></EVENT_MENTION>
                <EVENT_MENTION m_id="v2" pred="bailout" tense="PAST"><token_anchor t_id="3"/></EVENT_MENTION>
            </Markables>
            <Relations>
                <CLINK reltype="CAUSES" source="rule"><source m_id="v1"/><target m_id="v2"/></CLINK>
                <SLINK reltype="EPISTEMIC" source="speech"><source m_id="v1"/><target m_id="v2"/></SLINK>
            </Relations>
        </Document>
        """
        path = _write_tmp_xml(xml)
        doc = parse_meantime_xml(path)

        assert any(r.kind == "clink" and dict(r.attrs).get("reltype") == "CAUSES" for r in doc.relations)
        assert any(r.kind == "slink" and dict(r.attrs).get("reltype") == "EPISTEMIC" for r in doc.relations)


# ---------------------------------------------------------------------------
# Phase 5: APP head-span relaxation + CONJ virtual merge
# ---------------------------------------------------------------------------

def test_app_mention_relaxed_matches_nom_head_within_span():
    """APP gold with a wide span should relaxed-match a NOM prediction whose
    head token falls within the APP gold span (boundary mismatch recovery)."""
    # Gold APP span: tokens 16-22 (7 tokens).  Predicted NOM: single token 20.
    # Strict: different spans → no match.
    # Relaxed: pred head (20) is inside gold span → virtual head-span match.
    gold = {
        Mention(kind="entity", span=tuple(range(16, 23)), attrs=(("syntactic_type", "APP"),)),
    }
    pred = {
        Mention(kind="entity", span=(20,), attrs=(("syntactic_type", "NOM"),)),
    }
    strict = score_mention_layer(gold, pred, mode="strict")
    relaxed = score_mention_layer(gold, pred, mode="relaxed")

    assert strict["tp"] == 0, "strict should not match APP vs NOM with different spans"
    assert relaxed["tp"] == 1, "relaxed should match APP gold when pred head is within APP span"


def test_conj_virtual_merge_credits_when_conjuncts_matched():
    """Gold CONJ covering tokens 1-5 (e.g. 'India , China and Britain') should
    not be counted as FN when its individual conjunct predictions (tok 1, tok 3,
    tok 5) were all matched against sibling gold NAM mentions."""
    # Sibling NAM gold mentions and their matching predictions.
    gold = {
        Mention(kind="entity", span=(1,), attrs=(("syntactic_type", "NAM"),)),   # India
        Mention(kind="entity", span=(3,), attrs=(("syntactic_type", "NAM"),)),   # China
        Mention(kind="entity", span=(5,), attrs=(("syntactic_type", "NAM"),)),   # Britain
        # The CONJ parent spans all three conjuncts + commas.
        Mention(kind="entity", span=(1, 2, 3, 4, 5), attrs=(("syntactic_type", "CONJ"),)),
    }
    pred = {
        Mention(kind="entity", span=(1,), attrs=(("syntactic_type", "NAM"),)),
        Mention(kind="entity", span=(3,), attrs=(("syntactic_type", "NAM"),)),
        Mention(kind="entity", span=(5,), attrs=(("syntactic_type", "NAM"),)),
    }
    strict = score_mention_layer(gold, pred, mode="strict")
    relaxed = score_mention_layer(gold, pred, mode="relaxed")

    # Strict: CONJ unmatched → FN = 1, TP = 3.
    assert strict["tp"] == 3
    assert strict["fn"] == 1

    # Relaxed: CONJ virtually matched → FN = 0, TP = 3.
    assert relaxed["tp"] == 3
    assert relaxed["fn"] == 0


def test_conj_virtual_merge_does_not_fire_for_uncovered_conj():
    """A CONJ gold whose conjuncts were NOT predicted should still be FN
    in relaxed mode (virtual merge should not apply)."""
    gold = {
        Mention(kind="entity", span=(10, 11, 12, 13, 14), attrs=(("syntactic_type", "CONJ"),)),
    }
    pred = {
        # Completely different span, no overlap.
        Mention(kind="entity", span=(99,), attrs=(("syntactic_type", "NAM"),)),
    }
    relaxed = score_mention_layer(gold, pred, mode="relaxed")
    assert relaxed["fn"] == 1, "CONJ with no token coverage should remain FN"


def test_nam_head_span_relaxed_matches_partial_proper_name():
    """Phase 6: NAM predictions now benefit from head-span relaxation in relaxed mode.

    Gold: 'United States' spans tokens 14-15.  Prediction: 'States' at token 15
    (single-token NAM).  The prediction head (15) is the rightmost token of the
    gold span, so it should be a TP in relaxed mode even though IoU = 1/2 = 0.5
    (border-line) — and previously would have been < threshold for non-NOM types.
    With Phase 6 the head-span check fires for all entity types."""
    gold = {
        Mention(kind="entity", span=(14, 15), attrs=(("syntactic_type", "NAM"),)),
    }
    pred = {
        Mention(kind="entity", span=(15,), attrs=(("syntactic_type", "NAM"),)),
    }
    strict = score_mention_layer(gold, pred, mode="strict")
    relaxed = score_mention_layer(gold, pred, mode="relaxed")

    # Strict: spans differ → FP + FN.
    assert strict["tp"] == 0
    assert strict["fn"] == 1
    assert strict["fp"] == 1

    # Relaxed: pred head (15) is inside gold span {14,15} → TP.
    assert relaxed["tp"] == 1
    assert relaxed["fn"] == 0
    assert relaxed["fp"] == 0


def test_nam_head_span_no_false_match_on_disjoint_spans():
    """Phase 6 guard: a NAM prediction at token 7 should NOT match a gold NAM
    at tokens 14-15.  Their heads do not fall within each other's spans."""
    gold = {
        Mention(kind="entity", span=(14, 15), attrs=(("syntactic_type", "NAM"),)),
    }
    pred = {
        Mention(kind="entity", span=(7,), attrs=(("syntactic_type", "NAM"),)),
    }
    relaxed = score_mention_layer(gold, pred, mode="relaxed")
    assert relaxed["tp"] == 0
    assert relaxed["fn"] == 1
    assert relaxed["fp"] == 1


# ---------------------------------------------------------------------------
# Source-inspection: merged=false guards in projection queries
# ---------------------------------------------------------------------------

EVALUATOR_SRC = Path(__file__).resolve().parents[1] / "evaluation" / "meantime_evaluator.py"


def _evaluator_source() -> str:
    return EVALUATOR_SRC.read_text(encoding="utf-8")


@pytest.mark.unit
def test_tevent_projection_excludes_merged_events():
    """TEvent UNION branch must guard on coalesce(m.merged, false) = false
    so that secondary events collapsed by merge_aligns_with_event_clusters or
    collapse_light_verbs are never projected as independent events."""
    src = _evaluator_source()
    # Find the TEvent UNION branch (identified by TRIGGERS]->(m:TEvent))
    idx = src.find("[:TRIGGERS]->(m:TEvent)")
    assert idx != -1, "TEvent UNION branch not found in evaluator"
    # Look within the next 500 chars (the WHERE clause of that branch)
    branch = src[idx: idx + 500]
    assert "coalesce(m.merged, false) = false" in branch, (
        "TEvent projection branch must filter merged events; "
        "add AND coalesce(m.merged, false) = false to the WHERE clause"
    )


@pytest.mark.unit
def test_tlink_projection_excludes_merged_endpoints():
    """TLINK projection WHERE clause must guard on coalesce(a.merged, false)=false
    and coalesce(b.merged, false)=false so TLINKs anchored at merged secondary
    TEvents are not projected as false-positive relations."""
    src = _evaluator_source()
    idx = src.find("MATCH (a)-[r:TLINK]->(b)")
    assert idx != -1, "TLINK projection query not found in evaluator"
    # The guard must appear before the first OPTIONAL MATCH
    optional_idx = src.find("OPTIONAL MATCH", idx)
    tlink_scope = src[idx: optional_idx]
    assert "coalesce(a.merged, false) = false" in tlink_scope, (
        "TLINK projection must filter merged source endpoint"
    )
    assert "coalesce(b.merged, false) = false" in tlink_scope, (
        "TLINK projection must filter merged target endpoint"
    )


@pytest.mark.unit
def test_participant_projection_excludes_merged_tevent_endpoints():
    """Participant projection must not link entities to merged TEvents.
    The WHERE clause must include a guard that allows EventMentions through
    but blocks TEvents with merged=true."""
    src = _evaluator_source()
    idx = src.find("MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)")
    assert idx != -1, "Participant projection query not found in evaluator"
    # Look within the surrounding WHERE clause (next 400 chars)
    scope = src[idx: idx + 400]
    assert "evt:TEvent" in scope, "Participant query must reference TEvent label"
    assert "evt.merged" in scope, (
        "Participant projection must guard merged TEvent endpoints; "
        "add AND (NOT (evt:TEvent) OR coalesce(evt.merged, false) = false)"
    )
