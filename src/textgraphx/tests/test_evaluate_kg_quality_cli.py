"""Tests for KG quality evaluation CLI."""

import argparse
import json
from pathlib import Path

import pytest

from textgraphx.tools import evaluate_kg_quality


@pytest.mark.unit
def test_parser_requires_dataset_dir():
    parser = evaluate_kg_quality._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.unit
def test_dataset_file_discovery_filters_supported_extensions(tmp_path):
    (tmp_path / "a.xml").write_text("x", encoding="utf-8")
    (tmp_path / "b.naf").write_text("x", encoding="utf-8")
    (tmp_path / "c.txt").write_text("x", encoding="utf-8")
    (tmp_path / "d.json").write_text("x", encoding="utf-8")

    files = evaluate_kg_quality._dataset_files(tmp_path)
    assert [p.name for p in files] == ["a.xml", "b.naf", "c.txt"]


@pytest.mark.unit
def test_dataset_file_discovery_supports_subset_cap(tmp_path):
    for name in ["a.xml", "b.xml", "c.xml"]:
        (tmp_path / name).write_text("x", encoding="utf-8")

    files = evaluate_kg_quality._dataset_files(tmp_path, max_docs=2)
    assert [p.name for p in files] == ["a.xml", "b.xml"]


@pytest.mark.unit
def test_quality_tier_classification_boundaries():
    assert evaluate_kg_quality._quality_tier(0.95) == "PRODUCTION_READY"
    assert evaluate_kg_quality._quality_tier(0.85) == "ACCEPTABLE"
    assert evaluate_kg_quality._quality_tier(0.75) == "NEEDS_WORK"
    assert evaluate_kg_quality._quality_tier(0.65) == "RESEARCH_PHASE"


@pytest.mark.unit
def test_main_exports_all_formats_by_default(tmp_path, monkeypatch, capsys):
    dataset_dir = tmp_path / "dataset"
    out_dir = tmp_path / "out"
    dataset_dir.mkdir()
    (dataset_dir / "doc.naf").write_text("x", encoding="utf-8")

    class _FakeSuite:
        def overall_quality(self):
            return 0.91

        def conclusiveness(self):
            return (True, [])

        runtime_diagnostics = {
            "tlink_reciprocal_cycle_signals": [
                {"document_id": 41, "rel_type": "BEFORE", "cycle_count": 2}
            ],
            "temporal_anchor_connectivity_gaps": [
                {"document_id": 41, "connected_anchor_count": 0, "isolated_anchor_count": 3}
            ],
            "totals": {
                "entity_state_coverage_ratio": 0.25,
                "entity_mentions_with_state_count": 5,
                "tlink_anchor_inconsistent_count": 3,
                "tlink_anchor_self_link_count": 1,
                "tlink_anchor_endpoint_violation_count": 2,
                "tlink_anchor_filter_suppressed_count": 3,
                "tlink_missing_anchor_metadata_count": 0,
                "tlink_reciprocal_cycle_count": 2,
                "documents_with_temporal_connectivity_gaps_count": 1,
                "documents_without_temporal_tlinks_count": 1,
            }
        }

    class _FakeEvaluator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def evaluate(self, determinism_pass=None):
            assert determinism_pass is None
            return _FakeSuite()

        def export_json(self, suite, path):
            path.write_text("{}", encoding="utf-8")

        def export_csv(self, suite, path):
            path.write_text("metric,val\nq,0.91\n", encoding="utf-8")

        def export_markdown(self, suite, path):
            path.write_text("# report", encoding="utf-8")

    class _FakeGraph:
        def close(self):
            return None

    fake_cfg = argparse.Namespace(
        runtime=argparse.Namespace(
            mode="testing",
            strict_transition_gate=True,
            enable_cross_document_fusion=False,
        ),
        services=argparse.Namespace(
            temporal_url="http://temporal",
            coref_url="http://coref",
            srl_url="http://srl",
        ),
    )

    monkeypatch.setattr(evaluate_kg_quality, "_build_parser", evaluate_kg_quality._build_parser)

    def _fake_get_config():
        return fake_cfg

    monkeypatch.setitem(__import__("sys").modules, "textgraphx.config", argparse.Namespace(get_config=_fake_get_config))
    monkeypatch.setitem(
        __import__("sys").modules,
        "textgraphx.neo4j_client",
        argparse.Namespace(make_graph_from_config=lambda: _FakeGraph()),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "textgraphx.evaluation.fullstack_harness",
        argparse.Namespace(FullStackEvaluator=_FakeEvaluator),
    )

    rc = evaluate_kg_quality.main([
        "--dataset-dir",
        str(dataset_dir),
        "--output-dir",
        str(out_dir),
    ])

    assert rc == 0
    assert (out_dir / "kg_quality_report.json").exists()
    assert (out_dir / "kg_quality_scores.csv").exists()
    assert (out_dir / "kg_quality_report.md").exists()

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["entity_state_coverage_ratio"] == 0.25
    assert summary["entity_mentions_with_state_count"] == 5
    assert summary["tlink_anchor_inconsistent_count"] == 3
    assert summary["tlink_anchor_self_link_count"] == 1
    assert summary["tlink_anchor_endpoint_violation_count"] == 2
    assert summary["tlink_anchor_filter_suppressed_count"] == 3
    assert summary["tlink_missing_anchor_metadata_count"] == 0
    assert summary["temporal_findings"]["top_reciprocal_cycle_signal"]["document_id"] == 41
    assert summary["temporal_findings"]["documents_without_temporal_tlinks"] == [41]
    assert "KG quality operator summary:" in captured.err
    assert "tlink_anchor_inconsistent=3" in captured.err
    assert "missing_anchor_metadata=0" in captured.err
    assert "reciprocal_cycles=2" in captured.err
    assert "docs_without_temporal_tlinks=1" in captured.err


@pytest.mark.unit
def test_main_rejects_empty_dataset_dir(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()

    with pytest.raises(ValueError, match="No dataset files"):
        evaluate_kg_quality.main(["--dataset-dir", str(dataset_dir)])


@pytest.mark.unit
def test_main_supports_optional_baseline_comparison(tmp_path, monkeypatch, capsys):
    dataset_dir = tmp_path / "dataset"
    out_dir = tmp_path / "out"
    dataset_dir.mkdir()
    (dataset_dir / "doc.naf").write_text("x", encoding="utf-8")

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "overall_quality": 0.90,
                "structural_metrics": {"structural_health_score": 0.95},
                "semantic_metrics": {"semantic_compliance_score": 0.91},
                "temporal_metrics": {
                    "temporal_consistency_score": 0.92,
                    "tlink_reciprocal_cycle_count": 1,
                    "documents_with_temporal_connectivity_gaps_count": 0,
                    "documents_without_temporal_tlinks_count": 0,
                    "temporal_issue_count": 3,
                },
                "phase_quality_scores": {"mention_layer": 0.91},
            }
        ),
        encoding="utf-8",
    )

    class _FakeSuite:
        def overall_quality(self):
            return 0.84

        def conclusiveness(self):
            return (True, [])

        def quality_scores(self):
            return {"mention_layer": 0.84}

        runtime_diagnostics = {
            "tlink_reciprocal_cycle_signals": [
                {"document_id": 51, "rel_type": "BEFORE", "cycle_count": 1}
            ],
            "temporal_anchor_connectivity_gaps": [
                {"document_id": 51, "connected_anchor_count": 0, "isolated_anchor_count": 2}
            ],
            "totals": {
                "entity_state_coverage_ratio": 0.25,
                "entity_mentions_with_state_count": 5,
                "tlink_anchor_inconsistent_count": 3,
                "tlink_anchor_self_link_count": 1,
                "tlink_anchor_endpoint_violation_count": 2,
                "tlink_anchor_filter_suppressed_count": 3,
                "tlink_missing_anchor_metadata_count": 0,
                "tlink_reciprocal_cycle_count": 1,
                "documents_with_temporal_connectivity_gaps_count": 1,
                "documents_without_temporal_tlinks_count": 1,
            }
        }

    class _FakeEvaluator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def evaluate(self, determinism_pass=None):
            assert determinism_pass is None
            return _FakeSuite()

        def export_csv(self, suite, path):
            path.write_text("metric,val\nq,0.84\n", encoding="utf-8")

        def export_markdown(self, suite, path):
            path.write_text("# report", encoding="utf-8")

    class _FakeGraph:
        def close(self):
            return None

    fake_cfg = argparse.Namespace(
        runtime=argparse.Namespace(
            mode="testing",
            strict_transition_gate=True,
            enable_cross_document_fusion=False,
        ),
        services=argparse.Namespace(
            temporal_url="http://temporal",
            coref_url="http://coref",
            srl_url="http://srl",
        ),
    )

    def _fake_get_config():
        return fake_cfg

    monkeypatch.setitem(__import__("sys").modules, "textgraphx.config", argparse.Namespace(get_config=_fake_get_config))
    monkeypatch.setitem(
        __import__("sys").modules,
        "textgraphx.neo4j_client",
        argparse.Namespace(make_graph_from_config=lambda: _FakeGraph()),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "textgraphx.evaluation.fullstack_harness",
        argparse.Namespace(FullStackEvaluator=_FakeEvaluator),
    )

    rc = evaluate_kg_quality.main([
        "--dataset-dir",
        str(dataset_dir),
        "--output-dir",
        str(out_dir),
        "--baseline-report",
        str(baseline_path),
    ])

    assert rc == 0
    assert (out_dir / "kg_quality_report.json").exists()
    assert (out_dir / "kg_quality_comparison.json").exists()

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["comparison"]["is_regression"] is True
    assert summary["comparison"]["temporal_delta_details"]["tlink_reciprocal_cycle_count"] == pytest.approx(0.0)
    assert "temporal_delta_details" in json.loads((out_dir / "kg_quality_comparison.json").read_text(encoding="utf-8"))["comparison"]
    assert summary["regression_detected"] is True
    assert "KG quality comparison:" in captured.err
