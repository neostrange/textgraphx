"""M11: Full-Stack Integration Testing - End-to-end evaluation harness validation.

Tests the unified evaluation pipeline with real sample documents, validating:
  - FullStackEvaluator initialization and execution
  - Consolidated quality reporting with reasonable tiers
  - Phase-level metric aggregation
  - Runtime diagnostics collection
  - Report export formats (JSON, CSV, Markdown)
  - CI-like quality gate scenarios
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from textgraphx.evaluation.fullstack_harness import EvaluationSuite, FullStackEvaluator
from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import UnifiedMetricReport, create_unified_report


@pytest.fixture
def sample_dataset_dir(tmp_path) -> Path:
    """Create a minimal sample dataset with gold annotation files."""
    annotated_dir = tmp_path / "annotated"
    annotated_dir.mkdir()
    
    # Create sample MEANTIME-format XML annotations
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<TimeML xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="http://timeml.org/timeMLdocs/TimeML_1.2.1.xsd">
  <DOCID>76437</DOCID>
  <DCT><TIMEX3 tid="t0" type="DATE" value="2008-09-15">Monday , September 15 , 2008</TIMEX3></DCT>
  <TEXT>
    <SENTENCE id="s1">
      <TEXT>Markets have fallen sharply .</TEXT>
      <TLINK lid="l1" relType="INCLUDES" eventInstanceID="ei1" relatedToTime="t0"/>
      <EVENT eid="e1" eiid="ei1" tense="PRESENT" aspect="PERFECTIVE">
        <ANCHOR>fallen</ANCHOR>
      </EVENT>
      <TIMEX3 tid="t1" type="DATE" value="2008-09-15">Monday</TIMEX3>
    </SENTENCE>
  </TEXT>
</TimeML>"""
    
    (annotated_dir / "76437_sample.xml").write_text(sample_xml, encoding="utf-8")
    
    return annotated_dir


@pytest.fixture
def mock_graph():
    """Create a mock Neo4j graph for testing."""
    graph = MagicMock()
    
    # Mock graph queries to return sensible test data
    def mock_run(query: str, params: Optional[Dict[str, Any]] = None):
        result = MagicMock()
        
        # Return different data based on query pattern
        if "count(n)" in query and "EntityMention" in query:
            result.data.return_value = [{"c": 12}]
        elif "count(e)" in query and "EventMention" in query:
            result.data.return_value = [{"c": 8}]
        elif "count(t)" in query and "TIMEX" in query:
            result.data.return_value = [{"c": 5}]
        elif "count(r)" in query:
            result.data.return_value = [{"c": 15}]
        else:
            result.data.return_value = []
        
        return result
    
    graph.run = mock_run
    return graph


@pytest.mark.integration
def test_fullstack_evaluator_initialization(sample_dataset_dir: Path, mock_graph):
    """Test FullStackEvaluator setup with real dataset paths."""
    config_dict = {
        "runtime": {"mode": "test"},
        "services": {"temporal_url": "http://localhost:8080"},
    }
    
    evaluator = FullStackEvaluator(
        graph=mock_graph,
        dataset_paths=[sample_dataset_dir / "76437_sample.xml"],
        config_dict=config_dict,
        seed=42,
    )
    
    assert evaluator.graph is not None
    assert evaluator.runner is not None
    assert evaluator.runner.seed == 42
    assert evaluator.runner.fusion_enabled is False


@pytest.mark.integration
def test_evaluation_suite_quality_scoring():
    """Test EvaluationSuite quality score aggregation."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=True,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
        duration_seconds=123.45,
    )
    
    # Create mock reports with different quality scores
    mention_report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.85},
        run_metadata=run_metadata,
    )
    
    edge_report = create_unified_report(
        metric_type="edge_semantics_metrics",
        metrics={"quality_score": 0.75},
        run_metadata=run_metadata,
    )
    
    phase_report = create_unified_report(
        metric_type="phase_assertion_metrics",
        metrics={"quality_score": 0.90},
        run_metadata=run_metadata,
    )
    
    category_report = create_unified_report(
        metric_type="semantic_category_metrics",
        metrics={"quality_score": 0.80},
        run_metadata=run_metadata,
    )
    
    legacy_report = create_unified_report(
        metric_type="legacy_layer_metrics",
        metrics={"quality_score": 0.88},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=mention_report,
        edge_semantics=edge_report,
        phase_assertions=phase_report,
        semantic_categories=category_report,
        legacy_layer=legacy_report,
        elapsed_seconds=123.45,
        runtime_diagnostics={
            "totals": {
                "mentions_with_ent_class_count": 10,
                "glink_count": 5,
            }
        },
    )
    
    # Test quality score calculation
    overall_quality = suite.overall_quality()
    assert 0.80 <= overall_quality <= 0.90  # Should be between min and max
    
    # Test quality tiers
    quality_scores = suite.quality_scores()
    assert len(quality_scores) == 5
    assert quality_scores["mention_layer"] == 0.85
    assert quality_scores["edge_semantics"] == 0.75
    assert quality_scores["phase_assertions"] == 0.90


@pytest.mark.integration
def test_evaluation_suite_conclusiveness_detection():
    """Test conclusiveness checking for evaluation quality assurance."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=True,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
    )
    
    # Create report with inconclusive reasons
    mention_report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.85},
        run_metadata=run_metadata,
        inconclusive_reasons=["no_events_created", "backward_compat_violations=2"],
    )
    
    edge_report = create_unified_report(
        metric_type="edge_semantics_metrics",
        metrics={"quality_score": 0.75},
        run_metadata=run_metadata,
    )
    
    phase_report = create_unified_report(
        metric_type="phase_assertion_metrics",
        metrics={"quality_score": 0.90},
        run_metadata=run_metadata,
    )
    
    category_report = create_unified_report(
        metric_type="semantic_category_metrics",
        metrics={"quality_score": 0.80},
        run_metadata=run_metadata,
    )
    
    legacy_report = create_unified_report(
        metric_type="legacy_layer_metrics",
        metrics={"quality_score": 0.88},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=mention_report,
        edge_semantics=edge_report,
        phase_assertions=phase_report,
        semantic_categories=category_report,
        legacy_layer=legacy_report,
        elapsed_seconds=50.0,
    )
    
    # Check conclusiveness
    is_conclusive, reasons = suite.conclusiveness()
    assert not is_conclusive
    assert len(reasons) > 0
    assert any("no_events_created" in r for r in reasons)


@pytest.mark.integration
def test_evaluation_suite_to_dict_serialization():
    """Test EvaluationSuite JSON serialization for export."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=True,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
        duration_seconds=45.67,
    )
    
    # Create separate reports for each metric type
    mention_report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.85},
        run_metadata=run_metadata,
        feature_activation_evidence={"entity_mentions": 42},
    )
    
    edge_report = create_unified_report(
        metric_type="edge_semantics_metrics",
        metrics={"quality_score": 0.80},
        run_metadata=run_metadata,
    )
    
    phase_report = create_unified_report(
        metric_type="phase_assertion_metrics",
        metrics={"quality_score": 0.88},
        run_metadata=run_metadata,
    )
    
    category_report = create_unified_report(
        metric_type="semantic_category_metrics",
        metrics={"quality_score": 0.82},
        run_metadata=run_metadata,
    )
    
    legacy_report = create_unified_report(
        metric_type="legacy_layer_metrics",
        metrics={"quality_score": 0.90},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=mention_report,
        edge_semantics=edge_report,
        phase_assertions=phase_report,
        semantic_categories=category_report,
        legacy_layer=legacy_report,
        elapsed_seconds=45.67,
        runtime_diagnostics={
            "totals": {
                "phase_count": 5,
                "tlink_anchor_inconsistent_count": 3,
                "tlink_anchor_self_link_count": 1,
                "tlink_anchor_endpoint_violation_count": 2,
                "tlink_anchor_filter_suppressed_count": 3,
                "tlink_missing_anchor_metadata_count": 0,
            }
        },
    )
    
    suite_dict = suite.to_dict()
    
    # Validate structure
    assert suite_dict["execution_time_seconds"] == 45.67
    assert "quality_scores" in suite_dict
    assert "overall_quality" in suite_dict
    assert "conclusiveness" in suite_dict
    assert "reports" in suite_dict
    assert len(suite_dict["reports"]) == 5
    
    # Validate JSON serializable
    json_str = json.dumps(suite_dict, default=str)
    parsed = json.loads(json_str)
    assert parsed["execution_time_seconds"] == 45.67
    totals = parsed["runtime_diagnostics"]["totals"]
    assert totals["tlink_anchor_inconsistent_count"] == 3
    assert totals["tlink_anchor_self_link_count"] == 1
    assert totals["tlink_anchor_endpoint_violation_count"] == 2
    assert totals["tlink_anchor_filter_suppressed_count"] == 3
    assert totals["tlink_missing_anchor_metadata_count"] == 0


@pytest.mark.integration
def test_evaluation_suite_export_json(tmp_path):
    """Test JSON export functionality."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=False,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
        duration_seconds=30.5,
    )
    
    report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.92, "entities": 25},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=report,
        edge_semantics=report,
        phase_assertions=report,
        semantic_categories=report,
        legacy_layer=report,
        elapsed_seconds=30.5,
    )
    
    # Use mock evaluator for export
    mock_graph = MagicMock()
    
    # Create a real temp file for dataset hashing
    dataset_file = tmp_path / "sample.xml"
    dataset_file.write_text("<xml/>")
    
    evaluator = FullStackEvaluator(
        graph=mock_graph,
        dataset_paths=[dataset_file],
        config_dict={},
        seed=42,
    )
    
    output_path = tmp_path / "report.json"
    evaluator.export_json(suite, output_path)
    
    assert output_path.exists()
    exported_data = json.loads(output_path.read_text())
    assert exported_data["execution_time_seconds"] == 30.5
    assert exported_data["overall_quality"] > 0


@pytest.mark.integration
def test_evaluation_suite_export_markdown(tmp_path):
    """Test Markdown export with validity headers."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=True,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
        duration_seconds=28.3,
    )
    
    report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.88},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=report,
        edge_semantics=report,
        phase_assertions=report,
        semantic_categories=report,
        legacy_layer=report,
        elapsed_seconds=28.3,
        runtime_diagnostics={
            "totals": {
                "phase_count": 5,
                "doc_count": 3,
                "tlink_anchor_inconsistent_count": 2,
                "tlink_anchor_self_link_count": 1,
                "tlink_anchor_endpoint_violation_count": 1,
                "tlink_anchor_filter_suppressed_count": 2,
                "tlink_missing_anchor_metadata_count": 0,
            }
        },
    )
    
    mock_graph = MagicMock()
    
    # Create a real temp file for dataset hashing
    dataset_file = tmp_path / "sample.xml"
    dataset_file.write_text("<xml/>")
    
    evaluator = FullStackEvaluator(
        graph=mock_graph,
        dataset_paths=[dataset_file],
        config_dict={},
        seed=42,
    )
    
    output_path = tmp_path / "report.md"
    evaluator.export_markdown(suite, output_path)
    
    assert output_path.exists()
    content = output_path.read_text()
    assert "Full-Stack Evaluation Report" in content
    assert "Quality Scores" in content
    assert "Runtime Diagnostics" in content
    assert "tlink_anchor_inconsistent_count: 2" in content
    assert "tlink_anchor_self_link_count: 1" in content
    assert "tlink_anchor_endpoint_violation_count: 1" in content
    assert "tlink_anchor_filter_suppressed_count: 2" in content
    assert "tlink_missing_anchor_metadata_count: 0" in content
    assert "mention_layer_metrics" in content


@pytest.mark.integration
def test_fullstack_evaluator_export_csv(tmp_path):
    """Test CSV export for quality metrics comparison."""
    run_metadata = RunMetadata(
        dataset_hash="abc123",
        config_hash="def456",
        seed=42,
        strict_gate_enabled=False,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
        duration_seconds=35.2,
    )
    
    report = create_unified_report(
        metric_type="mention_layer_metrics",
        metrics={"quality_score": 0.86},
        run_metadata=run_metadata,
    )
    
    suite = EvaluationSuite(
        run_metadata=run_metadata,
        mention_layer=report,
        edge_semantics=report,
        phase_assertions=report,
        semantic_categories=report,
        legacy_layer=report,
        elapsed_seconds=35.2,
    )
    
    mock_graph = MagicMock()
    
    # Create a real temp file for dataset hashing
    dataset_file = tmp_path / "sample.xml"
    dataset_file.write_text("<xml/>")
    
    evaluator = FullStackEvaluator(
        graph=mock_graph,
        dataset_paths=[dataset_file],
        config_dict={},
        seed=42,
    )
    
    output_path = tmp_path / "scores.csv"
    evaluator.export_csv(suite, output_path)
    
    assert output_path.exists()
    csv_content = output_path.read_text()
    assert "metric_type" in csv_content
    assert "overall_quality" in csv_content


@pytest.mark.integration
def test_evaluation_suite_quality_tier_assignment():
    """Test quality tier classification for CI gating."""
    run_metadata = RunMetadata(
        dataset_hash="test",
        config_hash="test",
        seed=42,
        strict_gate_enabled=False,
        fusion_enabled=False,
        cleanup_mode="auto",
        timestamp="2026-04-06T12:00:00Z",
    )
    
    def make_suite_with_quality(quality_score: float) -> EvaluationSuite:
        report = create_unified_report(
            metric_type="test",
            metrics={"quality_score": quality_score},
            run_metadata=run_metadata,
        )
        return EvaluationSuite(
            run_metadata=run_metadata,
            mention_layer=report,
            edge_semantics=report,
            phase_assertions=report,
            semantic_categories=report,
            legacy_layer=report,
            elapsed_seconds=10.0,
        )
    
    # Test PRODUCTION_READY tier (>= 0.90)
    suite_prod = make_suite_with_quality(0.92)
    assert suite_prod.overall_quality() >= 0.90
    
    # Test ACCEPTABLE tier (>= 0.80)
    suite_acc = make_suite_with_quality(0.82)
    assert 0.80 <= suite_acc.overall_quality() < 0.90
    
    # Test NEEDS_WORK tier (>= 0.70)
    suite_work = make_suite_with_quality(0.75)
    assert 0.70 <= suite_work.overall_quality() < 0.80
    
    # Test RESEARCH_PHASE tier (< 0.70)
    suite_research = make_suite_with_quality(0.65)
    assert suite_research.overall_quality() < 0.70
