"""Milestone 8 tests: MEANTIME Bridge and Cross-Phase Validator.

Tests the integration of unified evaluation framework (M1-M7) with:
  - MEANTIME gold-standard evaluation (M8a)
  - Cross-phase consistency validation (M8b)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from textgraphx.evaluation.meantime_bridge import (
    MEANTIMEBridge,
    MEANTIMEResults,
    ConsolidatedQualityReport,
    LayerScores,
)
from textgraphx.evaluation.cross_phase_validator import (
    CrossPhaseValidator,
    ConsistencyReport,
    PhaseInvariantViolation,
    ViolationSeverity,
)
from textgraphx.evaluation.fullstack_harness import EvaluationSuite
from textgraphx.evaluation.report_validity import RunMetadata
from textgraphx.evaluation.unified_metrics import UnifiedMetricReport


# ============================================================================
# MEANTIME Bridge Tests (M8a)
# ============================================================================


class TestLayerScores:
    """Test LayerScores dataclass."""

    def test_layer_scores_creation(self):
        """Test creating layer score from components."""
        scores = LayerScores(
            layer_name="entity",
            strict_mode=False,
            tp=100,
            fp=10,
            fn=5,
            precision=0.909,
            recall=0.952,
            f1=0.930,
        )
        assert scores.layer_name == "entity"
        assert scores.f1 == 0.930
        assert not scores.strict_mode

    def test_layer_scores_from_prf_dict(self):
        """Test creating from precision_recall_f1 output."""
        prf_dict = {
            "tp": 100,
            "fp": 10,
            "fn": 5,
            "precision": 0.909,
            "recall": 0.952,
            "f1": 0.930,
        }
        scores = LayerScores.from_prf_dict("entity", False, prf_dict)
        assert scores.layer_name == "entity"
        assert scores.precision == 0.909
        assert scores.f1 == 0.930

    def test_layer_scores_to_dict(self):
        """Test serialization to dict."""
        scores = LayerScores(
            layer_name="event",
            strict_mode=True,
            tp=50,
            fp=5,
            fn=10,
            precision=0.909,
            recall=0.833,
            f1=0.868,
        )
        d = scores.to_dict()
        assert d["layer"] == "event"
        assert d["strict_mode"] is True
        assert d["f1"] == 0.868


class TestMEANTIMEResults:
    """Test MEANTIMEResults aggregation."""

    def test_meantime_results_creation(self):
        """Test creating MEANTIME results."""
        entity_strict = LayerScores(layer_name="entity", strict_mode=True, f1=0.85)
        entity_relaxed = LayerScores(layer_name="entity", strict_mode=False, f1=0.92)
        event_strict = LayerScores(layer_name="event", strict_mode=True, f1=0.75)
        event_relaxed = LayerScores(layer_name="event", strict_mode=False, f1=0.88)
        timex_strict = LayerScores(layer_name="timex", strict_mode=True, f1=0.70)
        timex_relaxed = LayerScores(layer_name="timex", strict_mode=False, f1=0.82)

        results = MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity_strict,
            entity_relaxed=entity_relaxed,
            event_strict=event_strict,
            event_relaxed=event_relaxed,
            timex_strict=timex_strict,
            timex_relaxed=timex_relaxed,
        )
        assert results.doc_id == "doc1"
        assert results.entity_relaxed.f1 == 0.92

    def test_meantime_macro_layer_f1(self):
        """Test macro F1 computation across layers."""
        entity = LayerScores(layer_name="entity", strict_mode=False, f1=0.90)
        event = LayerScores(layer_name="event", strict_mode=False, f1=0.80)
        timex = LayerScores(layer_name="timex", strict_mode=False, f1=0.85)

        results = MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity,
            entity_relaxed=entity,
            event_strict=event,
            event_relaxed=event,
            timex_strict=timex,
            timex_relaxed=timex,
        )
        macro = results.macro_layer_f1(mode="relaxed")
        expected = (0.90 + 0.80 + 0.85) / 3
        assert abs(macro["macro_f1"] - expected) < 0.01
        assert macro["count"] == 3

    def test_meantime_macro_all_f1(self):
        """Test macro F1 including relations."""
        entity = LayerScores(layer_name="entity", strict_mode=False, f1=0.90)
        event = LayerScores(layer_name="event", strict_mode=False, f1=0.80)
        timex = LayerScores(layer_name="timex", strict_mode=False, f1=0.85)
        tlink = LayerScores(layer_name="tlink", strict_mode=False, f1=0.75)

        results = MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity,
            entity_relaxed=entity,
            event_strict=event,
            event_relaxed=event,
            timex_strict=timex,
            timex_relaxed=timex,
            relation_scores={"tlink": tlink},
        )
        macro = results.macro_all_f1(mode="relaxed")
        expected = (0.90 + 0.80 + 0.85 + 0.75) / 4
        assert abs(macro - expected) < 0.01

    def test_meantime_results_to_dict(self):
        """Test serialization to dict."""
        entity = LayerScores(layer_name="entity", strict_mode=False, f1=0.90)
        event = LayerScores(layer_name="event", strict_mode=False, f1=0.80)
        timex = LayerScores(layer_name="timex", strict_mode=False, f1=0.85)

        results = MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity,
            entity_relaxed=entity,
            event_strict=event,
            event_relaxed=event,
            timex_strict=timex,
            timex_relaxed=timex,
            evaluation_note="Test evaluation",
        )
        d = results.to_dict()
        assert d["doc_id"] == "doc1"
        assert d["evaluation_note"] == "Test evaluation"
        assert "mention_layers" in d
        assert "entity" in d["mention_layers"]


class TestConsolidatedQualityReport:
    """Test consolidated quality report."""

    @pytest.fixture
    def mock_evaluation_suite(self):
        """Create mock evaluation suite."""
        from textgraphx.evaluation.report_validity import RunMetadata
        metadata = RunMetadata(
            timestamp="2025-04-05T12:00:00Z",
            dataset_hash="hash1",
            config_hash="config1",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=True,
            cleanup_mode="auto",
        )
        suite = Mock(spec=EvaluationSuite)
        suite.run_metadata = metadata
        suite.overall_quality = Mock(return_value=0.85)
        suite.quality_scores = Mock(return_value={
            "mention_layer": 0.85,
            "edge_semantics": 0.80,
            "phase_assertions": 0.90,
            "semantic_categories": 0.82,
            "legacy_layer": 0.88,
        })
        suite.conclusiveness = Mock(return_value=(True, []))
        return suite

    @pytest.fixture
    def mock_meantime_results(self):
        """Create mock MEANTIME results."""
        entity = LayerScores(layer_name="entity", strict_mode=False, f1=0.88)
        event = LayerScores(layer_name="event", strict_mode=False, f1=0.82)
        timex = LayerScores(layer_name="timex", strict_mode=False, f1=0.80)

        return MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity,
            entity_relaxed=entity,
            event_strict=event,
            event_relaxed=event,
            timex_strict=timex,
            timex_relaxed=timex,
        )

    def test_consolidated_report_creation(self, mock_evaluation_suite, mock_meantime_results):
        """Test creating consolidated report."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        assert report.evaluation_suite == mock_evaluation_suite
        assert report.meantime_results == mock_meantime_results

    def test_phase_quality_score(self, mock_evaluation_suite, mock_meantime_results):
        """Test phase quality extraction."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        assert report.phase_quality_score() == 0.85

    def test_meantime_quality_score(self, mock_evaluation_suite, mock_meantime_results):
        """Test MEANTIME quality extraction."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        # (0.88 + 0.82 + 0.80) / 3 = 0.8333...
        meantime_score = report.meantime_quality_score()
        assert abs(meantime_score - 0.833) < 0.01

    def test_consistency_score_agreement(self, mock_evaluation_suite, mock_meantime_results):
        """Test consistency when phase and MEANTIME scores agree."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        consistency = report.consistency_score()
        # Phase=0.85, MEANTIME≈0.833, delta≈0.017
        # consistency = 1.0 - 0.017 = 0.983
        assert consistency > 0.98

    def test_consistency_score_divergence(self, mock_evaluation_suite, mock_meantime_results):
        """Test consistency when scores diverge."""
        mock_evaluation_suite.overall_quality = Mock(return_value=0.95)  # High phase
        # MEANTIME ≈ 0.833, so delta = 0.117, consistency ≈ 0.883
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        consistency = report.consistency_score()
        assert consistency < 0.90

    def test_overall_quality(self, mock_evaluation_suite, mock_meantime_results):
        """Test weighted overall quality computation."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
            weight_phase_quality=0.40,
            weight_meantime_f1=0.40,
            weight_consistency=0.20,
        )
        overall = report.overall_quality()
        # Phase=0.85, MEANTIME≈0.833, Consistency≈0.983
        # Overall = 0.85*0.4 + 0.833*0.4 + 0.983*0.2
        #         = 0.34 + 0.3332 + 0.1966 ≈ 0.8698
        assert abs(overall - 0.87) < 0.05

    def test_quality_tier_production_ready(self, mock_evaluation_suite, mock_meantime_results):
        """Test quality tier assignment for production-ready."""
        # Mock high quality suite
        # Need: 0.95*0.5 + 0.9*0.4 + 0.95*0.1 = 0.475 + 0.36 + 0.095 = 0.93 > 0.90
        mock_evaluation_suite.overall_quality = Mock(return_value=0.95)
        # Adjust meantime to be higher
        entity_high = LayerScores(layer_name="entity", strict_mode=False, f1=0.92)
        event_high = LayerScores(layer_name="event", strict_mode=False, f1=0.90)
        timex_high = LayerScores(layer_name="timex", strict_mode=False, f1=0.88)

        meantime_high = MEANTIMEResults(
            doc_id="doc1",
            entity_strict=entity_high,
            entity_relaxed=entity_high,
            event_strict=event_high,
            event_relaxed=event_high,
            timex_strict=timex_high,
            timex_relaxed=timex_high,
        )
        # macro F1 = (0.92+0.90+0.88)/3 = 0.9
        
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=meantime_high,
            weight_phase_quality=0.50,
            weight_meantime_f1=0.40,
            weight_consistency=0.10,
        )
        # Score = 0.95*0.5 + 0.90*0.4 + high*0.1 = 0.475 + 0.36 + 0.1 = 0.935 > 0.90
        tier = report.quality_tier()
        assert tier == "PRODUCTION_READY", f"Expected PRODUCTION_READY but got {tier} (score={report.overall_quality():.4f})"

    def test_quality_tier_needs_work(self, mock_evaluation_suite, mock_meantime_results):
        """Test quality tier assignment for needs work."""
        mock_evaluation_suite.overall_quality = Mock(return_value=0.65)
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        assert report.quality_tier() == "NEEDS_WORK"

    def test_passed_quality_gate(self, mock_evaluation_suite, mock_meantime_results):
        """Test quality gate pass/fail."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
            weight_phase_quality=0.50,
            weight_meantime_f1=0.50,
            weight_consistency=0.0,
        )
        # Score ≈ 0.85 * 0.5 + 0.833 * 0.5 ≈ 0.842
        assert report.passed_quality_gate(threshold=0.80) is True
        assert report.passed_quality_gate(threshold=0.90) is False

    def test_consolidated_report_to_dict(self, mock_evaluation_suite, mock_meantime_results):
        """Test serialization to dict."""
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        d = report.to_dict()
        assert "evaluation_dimensions" in d
        assert "consolidated_quality" in d
        assert d["consolidated_quality"]["passed_gate"] is True

    def test_consolidated_report_to_markdown(self, mock_evaluation_suite, mock_meantime_results):
        """Test markdown report generation."""
        mock_evaluation_suite.to_dict = Mock(return_value={"test": "data"})
        report = ConsolidatedQualityReport(
            run_metadata=mock_evaluation_suite.run_metadata,
            evaluation_suite=mock_evaluation_suite,
            meantime_results=mock_meantime_results,
        )
        markdown = report.to_markdown()
        assert "Consolidated Evaluation Report" in markdown
        assert "Overall Quality" in markdown
        assert "PRODUCTION_READY" in markdown or "ACCEPTABLE" in markdown


class TestMEANTIMEBridge:
    """Test MEANTIME Bridge."""

    def test_bridge_initialization_missing_file(self, tmp_path):
        """Test bridge initialization with missing gold XML."""
        gold_path = tmp_path / "nonexistent.xml"
        with pytest.raises(FileNotFoundError):
            MEANTIMEBridge(gold_xml_path=gold_path)

    def test_bridge_initialization_success(self, tmp_path):
        """Test successful bridge initialization."""
        gold_path = tmp_path / "gold.xml"
        gold_path.write_text('<?xml version="1.0"?><annotations doc_id="test"/>')

        bridge = MEANTIMEBridge(gold_xml_path=gold_path)
        assert bridge.gold_xml_path == gold_path
        assert bridge.discourse_only is False


# ============================================================================
# Cross-Phase Validator Tests (M8b)
# ============================================================================


class TestPhaseInvariantViolation:
    """Test violation dataclass."""

    def test_violation_creation(self):
        """Test creating violation."""
        v = PhaseInvariantViolation(
            phase_from="Phase 2",
            phase_to="Phase 3",
            rule_name="cascade_test",
            severity=ViolationSeverity.WARNING,
            message="Test violation",
            count=5,
        )
        assert v.rule_name == "cascade_test"
        assert v.severity == ViolationSeverity.WARNING
        assert v.count == 5

    def test_violation_to_dict(self):
        """Test serialization."""
        v = PhaseInvariantViolation(
            phase_from="Phase 2",
            phase_to="Phase 3",
            rule_name="test",
            severity=ViolationSeverity.ERROR,
            message="Error test",
            count=3,
            examples=["ex1", "ex2", "ex3", "ex4"],
        )
        d = v.to_dict()
        assert d["severity"] == "error"
        assert d["count"] == 3
        assert len(d["examples"]) <= 3


class TestConsistencyReport:
    """Test consistency report."""

    def test_consistency_report_empty(self):
        """Test empty consistency report."""
        report = ConsistencyReport()
        assert report.error_count() == 0
        assert report.warning_count() == 0
        assert report.is_consistent() is True

    def test_consistency_report_with_errors(self):
        """Test report with errors."""
        v1 = PhaseInvariantViolation(
            phase_from="P1", phase_to="P2",
            rule_name="test",
            severity=ViolationSeverity.ERROR,
            message="Error",
        )
        v2 = PhaseInvariantViolation(
            phase_from="P2", phase_to="P3",
            rule_name="test2",
            severity=ViolationSeverity.WARNING,
            message="Warning",
        )
        report = ConsistencyReport(violations=[v1, v2])
        assert report.error_count() == 1
        assert report.warning_count() == 1
        assert report.is_consistent() is False
        assert report.is_consistent(allow_warnings=True) is False

    def test_consistency_report_with_warnings_only(self):
        """Test report with only warnings."""
        v = PhaseInvariantViolation(
            phase_from="P1", phase_to="P2",
            rule_name="test",
            severity=ViolationSeverity.WARNING,
            message="Warning",
        )
        report = ConsistencyReport(violations=[v])
        assert report.error_count() == 0
        assert report.warning_count() == 1
        assert report.is_consistent() is False
        assert report.is_consistent(allow_warnings=True) is True

    def test_consistency_score(self):
        """Test consistency score computation."""
        # No violations = 1.0
        report1 = ConsistencyReport()
        assert report1.consistency_score() == 1.0

        # 1 error = 1.0 - 0.1 = 0.9
        v_error = PhaseInvariantViolation(
            phase_from="P1", phase_to="P2",
            rule_name="test",
            severity=ViolationSeverity.ERROR,
            message="Error",
        )
        report2 = ConsistencyReport(violations=[v_error])
        assert abs(report2.consistency_score() - 0.9) < 0.01

        # 1 warning = 1.0 - 0.05 = 0.95
        v_warn = PhaseInvariantViolation(
            phase_from="P1", phase_to="P2",
            rule_name="test",
            severity=ViolationSeverity.WARNING,
            message="Warning",
        )
        report3 = ConsistencyReport(violations=[v_warn])
        assert abs(report3.consistency_score() - 0.95) < 0.01

    def test_consistency_report_to_dict(self):
        """Test serialization."""
        v = PhaseInvariantViolation(
            phase_from="P1", phase_to="P2",
            rule_name="test",
            severity=ViolationSeverity.WARNING,
            message="Warning",
        )
        report = ConsistencyReport(
            violations=[v],
            phase_density_metrics={"events": 100},
            orphaned_nodes={"EventMention": 5},
        )
        d = report.to_dict()
        assert d["consistency_check"]["is_consistent"] is False
        assert d["consistency_check"]["error_count"] == 0
        assert len(d["violations"]) == 1

    def test_consistency_report_to_markdown(self):
        """Test markdown generation."""
        v = PhaseInvariantViolation(
            phase_from="P2", phase_to="P3",
            rule_name="cascade",
            severity=ViolationSeverity.WARNING,
            message="Cascade issue",
        )
        report = ConsistencyReport(
            violations=[v],
            orphaned_nodes={"EventMention": 10},
        )
        markdown = report.to_markdown()
        assert "Cross-Phase Consistency Report" in markdown
        assert "Orphaned Nodes" in markdown
        assert "EventMention: 10" in markdown


class TestCrossPhaseValidator:
    """Test cross-phase validation."""

    @pytest.fixture
    def mock_evaluation_suite(self):
        """Create mock suite."""
        suite = Mock(spec=EvaluationSuite)
        suite.quality_scores = Mock(return_value={
            "mention_layer": 0.85,
            "edge_semantics": 0.80,
            "phase_assertions": 0.90,
            "semantic_categories": 0.82,
            "legacy_layer": 0.88,
        })
        return suite

    @pytest.fixture
    def mock_graph(self):
        """Create mock Neo4j graph."""
        graph = Mock()
        return graph

    def test_validator_initialization(self, mock_graph, mock_evaluation_suite):
        """Test validator initialization."""
        validator = CrossPhaseValidator(
            graph=mock_graph,
            evaluation_suite=mock_evaluation_suite,
        )
        assert validator.graph == mock_graph
        assert validator.evaluation_suite == mock_evaluation_suite

    def test_validator_validate(self, mock_graph, mock_evaluation_suite):
        """Test validation runs without error."""
        validator = CrossPhaseValidator(
            graph=mock_graph,
            evaluation_suite=mock_evaluation_suite,
        )
        # Mock graph.run to raise error (graph unavailable)
        def side_effect(*args, **kwargs):
            raise Exception("Graph unavailable")
        
        validator.graph.run = Mock(side_effect=side_effect)

        report = validator.validate()
        assert isinstance(report, ConsistencyReport)
        # Should have recorded the error handling gracefully (may have warnings)
        # No assertion on violations since validate catches errors gracefully

    def test_phase_cascade_check_divergence(self, mock_graph, mock_evaluation_suite):
        """Test cascade check detects divergence."""
        # High mention quality but low edge quality
        mock_evaluation_suite.quality_scores = Mock(return_value={
            "mention_layer": 0.90,
            "edge_semantics": 0.50,  # Low
            "phase_assertions": 0.90,
            "semantic_categories": 0.82,
            "legacy_layer": 0.88,
        })
        validator = CrossPhaseValidator(
            graph=mock_graph,
            evaluation_suite=mock_evaluation_suite,
        )
        validator.graph.run = Mock(side_effect=Exception("N/A"))

        report = validator.validate()
        # Should detect cascade issue
        cascade_violations = [v for v in report.violations if "cascade" in v.rule_name]
        assert len(cascade_violations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
