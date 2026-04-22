"""Milestone 9-10 tests: Regression Detection and CI/CD Integration.

Tests for quality regression detection, variance analysis, and CI/CD gate
enforcement with GitHub Actions and local pre-commit integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
import json
from statistics import mean

from textgraphx.evaluation.regression_detector import (
    BaselineMetrics,
    BaselineManager,
    RegressionDetector,
    RegressionAnalysis,
    VarianceAnalyzer,
    VarianceReport,
    QualityGateVerifier,
)
from textgraphx.evaluation.ci_integration import (
    QualityGateConfig,
    QualityGateResult,
    QualityGateVerifierCI,
    CIReportGenerator,
    QualityTrendTracker,
    LocalPrecommitChecker,
)


# ============================================================================
# M9: Regression Detection Tests
# ============================================================================


class TestBaselineMetrics:
    """Test baseline metrics capture."""

    def test_baseline_creation(self):
        """Test creating baseline metrics."""
        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.85,
            phase_scores={"m1": 0.90, "m2": 0.85},
            meantime_f1=0.82,
            consistency_score=0.95,
        )
        assert baseline.quality_score == 0.85
        assert len(baseline.phase_scores) == 2

    def test_baseline_serialization(self):
        """Test baseline to/from dict."""
        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.85,
            phase_scores={"m1": 0.90},
        )
        d = baseline.to_dict()
        baseline2 = BaselineMetrics.from_dict(d)
        assert baseline2.quality_score == baseline.quality_score


class TestBaselineManager:
    """Test baseline persistence."""

    def test_baseline_save_and_load(self, tmp_path):
        """Test saving and loading baselines."""
        manager = BaselineManager(baseline_dir=tmp_path)

        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.85,
            phase_scores={"m1": 0.90},
        )

        # Save baseline directly
        filepath = tmp_path / "baseline_v1_0.json"
        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f)

        # Load it back
        loaded = manager.load_baseline("v1.0")
        assert loaded is not None
        assert loaded.quality_score == 0.85

    def test_list_baselines(self, tmp_path):
        """Test listing available baselines."""
        manager = BaselineManager(baseline_dir=tmp_path)

        # Create some baseline files
        for version in ["v1.0", "v1.1"]:
            baseline = BaselineMetrics(
                timestamp="2025-04-05T12:00:00Z",
                version=version,
                quality_score=0.85,
            )
            filepath = tmp_path / f"baseline_{version.replace('.', '_')}.json"
            with open(filepath, "w") as f:
                json.dump(baseline.to_dict(), f)

        baselines = manager.list_baselines()
        assert "v1.0" in baselines
        assert "v1.1" in baselines


class TestRegressionDetector:
    """Test regression detection."""

    @pytest.fixture
    def mock_report(self):
        """Create mock report."""
        report = Mock()
        report.run_metadata = Mock()
        report.run_metadata.config_hash = "cfg1"
        report.run_metadata.dataset_hash = "ds1"
        report.overall_quality = Mock(return_value=0.83)
        report.evaluation_suite.quality_scores = Mock(return_value={
            "m1": 0.85,
            "m2": 0.80,
        })
        return report

    def test_regression_detection(self, mock_report, tmp_path):
        """Test detecting regression."""
        manager = BaselineManager(baseline_dir=tmp_path)

        # Save baseline
        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.85,
            phase_scores={"m1": 0.87, "m2": 0.82},
        )
        filepath = tmp_path / "baseline_v1_0.json"
        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f)

        # Detect regression (mock has lower quality)
        detector = RegressionDetector(baseline_manager=manager)
        analysis = detector.detect(mock_report, "v1.0")

        assert analysis.baseline_quality == 0.85
        assert analysis.current_quality == 0.83
        assert analysis.quality_delta < 0  # Negative = regression

    def test_no_regression(self, mock_report, tmp_path):
        """Test when no regression occurs."""
        manager = BaselineManager(baseline_dir=tmp_path)

        # Baseline lower than current
        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.80,
        )
        filepath = tmp_path / "baseline_v1_0.json"
        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f)

        detector = RegressionDetector(baseline_manager=manager)
        analysis = detector.detect(mock_report, "v1.0")

        assert analysis.quality_delta > 0  # Positive = improvement
        assert not analysis.is_regression

    def test_regression_analysis_to_dict(self, mock_report, tmp_path):
        """Test regression analysis serialization."""
        manager = BaselineManager(baseline_dir=tmp_path)
        baseline = BaselineMetrics(
            timestamp="2025-04-05T12:00:00Z",
            version="v1.0",
            quality_score=0.85,
        )
        filepath = tmp_path / "baseline_v1_0.json"
        with open(filepath, "w") as f:
            json.dump(baseline.to_dict(), f)

        detector = RegressionDetector(baseline_manager=manager)
        analysis = detector.detect(mock_report, "v1.0")

        d = analysis.to_dict()
        assert "baseline_quality" in d
        assert "current_quality" in d
        assert "severity" in d


class TestVarianceAnalyzer:
    """Test variance analysis."""

    def test_variance_deterministic(self):
        """Test detecting deterministic run."""
        analyzer = VarianceAnalyzer()

        # Identical scores
        scores = [0.8500, 0.8500, 0.8500]
        report = analyzer.analyze(scores)

        assert report.run_count == 3
        assert report.std_dev == 0.0
        assert report.is_deterministic

    def test_variance_non_deterministic(self):
        """Test detecting non-deterministic run."""
        analyzer = VarianceAnalyzer(determinism_tolerance=0.0001)

        # Varying scores
        scores = [0.8400, 0.8500, 0.8600]
        report = analyzer.analyze(scores)

        assert report.run_count == 3
        assert report.std_dev > 0
        assert not report.is_deterministic

    def test_variance_single_run(self):
        """Test with single run."""
        analyzer = VarianceAnalyzer()
        scores = [0.85]
        report = analyzer.analyze(scores)

        assert report.run_count == 1
        assert report.std_dev == 0.0
        assert report.is_deterministic

    def test_variance_report_to_dict(self):
        """Test variance report serialization."""
        analyzer = VarianceAnalyzer()
        scores = [0.84, 0.85, 0.86]
        report = analyzer.analyze(scores)

        d = report.to_dict()
        assert d["run_count"] == 3
        assert "mean_quality" in d
        assert "std_dev" in d


class TestQualityGateVerifier:
    """Test statistical significance verification."""

    def test_significant_improvement(self):
        """Test detecting significant improvement."""
        verifier = QualityGateVerifier()

        baseline = 0.80
        current = [0.85, 0.86, 0.85]  # Clearly better

        is_sig, msg = verifier.verify_improvement(baseline, current)
        assert is_sig
        assert "significant" in msg.lower()

    def test_not_significant(self):
        """Test when improvement is not significant."""
        verifier = QualityGateVerifier()

        baseline = 0.850
        current = [0.851, 0.850, 0.849]  # Essentially same

        is_sig, msg = verifier.verify_improvement(baseline, current)
        assert not is_sig
        assert "random" in msg.lower()

    def test_insufficient_runs(self):
        """Test with insufficient runs."""
        verifier = QualityGateVerifier(min_runs=3)

        baseline = 0.85
        current = [0.86]  # Only 1 run

        is_sig, msg = verifier.verify_improvement(baseline, current)
        assert not is_sig
        assert "at least 3" in msg.lower()


# ============================================================================
# M10: CI/CD Integration Tests
# ============================================================================


class TestQualityGateConfig:
    """Test quality gate configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = QualityGateConfig()
        assert config.min_overall_quality == 0.80
        assert config.require_no_errors

    def test_strict_config(self):
        """Test strict configuration."""
        config = QualityGateConfig.strict()
        assert config.min_overall_quality == 0.90
        assert config.min_phase_quality == 0.85

    def test_relaxed_config(self):
        """Test relaxed configuration."""
        config = QualityGateConfig.relaxed()
        assert config.min_overall_quality == 0.70
        assert not config.require_no_errors

    def test_config_serialization(self):
        """Test config to/from dict."""
        config = QualityGateConfig(min_overall_quality=0.85)
        d = config.to_dict()
        config2 = QualityGateConfig.from_dict(d)
        assert config2.min_overall_quality == 0.85


class TestQualityGateVerifierCI:
    """Test CI quality gate verification."""

    @pytest.fixture
    def mock_report(self):
        """Create mock report."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.85)
        report.evaluation_suite.quality_scores = Mock(return_value={
            "m1": 0.85,
            "m2": 0.80,
            "m3": 0.88,
        })
        report.meantime_quality_score = Mock(return_value=0.82)
        report.consistency_score = Mock(return_value=0.92)
        report.run_metadata = Mock()
        report.run_metadata.seed = 42
        return report

    def test_gate_pass(self, mock_report):
        """Test passing quality gate."""
        verifier = QualityGateVerifierCI()
        result = verifier.verify(mock_report)

        assert result.passed
        assert len(result.violations) == 0

    def test_gate_fail_quality_too_low(self):
        """Test failing due to low quality."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.65)
        report.evaluation_suite.quality_scores = Mock(return_value={"m1": 0.60})
        report.meantime_quality_score = Mock(return_value=0.70)
        report.consistency_score = Mock(return_value=0.85)
        report.run_metadata = Mock(seed=42)

        verifier = QualityGateVerifierCI()
        result = verifier.verify(report)

        assert not result.passed
        assert any("overall" in v.lower() for v in result.violations)

    def test_gate_fail_phase_quality(self):
        """Test failing due to low phase quality."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.80)
        report.evaluation_suite.quality_scores = Mock(return_value={"m1": 0.50})  # Too low
        report.meantime_quality_score = Mock(return_value=0.80)
        report.consistency_score = Mock(return_value=0.90)
        report.run_metadata = Mock(seed=42)

        verifier = QualityGateVerifierCI()
        result = verifier.verify(report)

        assert not result.passed
        assert any("m1" in v.lower() for v in result.violations)

    def test_gate_result_to_dict(self, mock_report):
        """Test result serialization."""
        verifier = QualityGateVerifierCI()
        result = verifier.verify(mock_report)

        d = result.to_dict()
        assert d["passed"] == True
        assert "overall_score" in d

    def test_gate_result_to_github_output(self, mock_report):
        """Test GitHub Actions output."""
        verifier = QualityGateVerifierCI()
        result = verifier.verify(mock_report)

        output = result.to_github_actions_output()
        assert "notice" in output or "error" in output
        assert "Quality Gate" in output

    def test_gate_result_to_pr_comment(self, mock_report):
        """Test PR comment generation."""
        verifier = QualityGateVerifierCI()
        result = verifier.verify(mock_report)

        comment = result.to_pr_comment()
        assert "Quality Gate" in comment
        assert "PASSED" in comment or "FAILED" in comment

    def test_gate_result_exit_code(self, mock_report):
        """Test exit code conversion."""
        verifier = QualityGateVerifierCI()
        result = verifier.verify(mock_report)

        assert result.to_exit_code() == 0  # Passed


class TestCIReportGenerator:
    """Test CI report generation."""

    @pytest.fixture
    def mock_result(self, mock_report):
        """Create mock gate result."""
        verifier = QualityGateVerifierCI()
        return verifier.verify(mock_report)

    @pytest.fixture
    def mock_report(self):
        """Create mock report."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.85)
        report.evaluation_suite.quality_scores = Mock(return_value={"m1": 0.85})
        report.meantime_quality_score = Mock(return_value=0.82)
        report.consistency_score = Mock(return_value=0.92)
        report.run_metadata = Mock(seed=42)
        return report

    def test_json_report_generation(self, mock_result, tmp_path):
        """Test JSON report generation."""
        json_str = CIReportGenerator.json_report(mock_result)
        data = json.loads(json_str)

        assert "gate_result" in data
        assert data["gate_result"]["passed"]

    def test_json_report_to_file(self, mock_result, tmp_path):
        """Test JSON report file writing."""
        outfile = tmp_path / "report.json"
        path = CIReportGenerator.json_report(mock_result, output_path=outfile)

        assert path.exists()
        assert path == outfile

    def test_markdown_report_generation(self, mock_result):
        """Test markdown report generation."""
        markdown = CIReportGenerator.markdown_report(mock_result)

        assert "Quality Gate" in markdown
        assert "PASSED" in markdown or "FAILED" in markdown

    def test_markdown_report_to_file(self, mock_result, tmp_path):
        """Test markdown report file writing."""
        outfile = tmp_path / "report.md"
        path = CIReportGenerator.markdown_report(mock_result, output_path=outfile)

        assert path.exists()
        assert path == outfile


class TestQualityTrendTracker:
    """Test quality trend tracking."""

    def test_trend_tracking(self, tmp_path):
        """Test recording and querying trends."""
        tracker = QualityTrendTracker(trend_file=tmp_path / "trend.json")

        # Record some points
        report1 = Mock()
        report1.run_metadata = Mock(timestamp="2025-04-01T12:00:00Z")
        report1.overall_quality = Mock(return_value=0.80)

        report2 = Mock()
        report2.run_metadata = Mock(timestamp="2025-04-02T12:00:00Z")
        report2.overall_quality = Mock(return_value=0.85)

        tracker.record(report1)
        tracker.record(report2)

        assert len(tracker.points) == 2
        summary = tracker.trend_summary()
        assert summary["earliest_score"] == 0.80
        assert summary["latest_score"] == 0.85
        assert "improving" in summary["trend_direction"]

    def test_trend_persistence(self, tmp_path):
        """Test loading persisted trends."""
        trend_file = tmp_path / "trend.json"
        tracker1 = QualityTrendTracker(trend_file=trend_file)

        report = Mock()
        report.run_metadata = Mock(timestamp="2025-04-01T12:00:00Z")
        report.overall_quality = Mock(return_value=0.82)

        tracker1.record(report)

        # Load in new tracker
        tracker2 = QualityTrendTracker(trend_file=trend_file)
        assert len(tracker2.points) == 1
        assert tracker2.points[0].quality_score == 0.82

    def test_trend_markdown(self, tmp_path):
        """Test trend report generation."""
        tracker = QualityTrendTracker(trend_file=tmp_path / "trend.json")

        report = Mock()
        report.run_metadata = Mock(timestamp="2025-04-01T12:00:00Z")
        report.overall_quality = Mock(return_value=0.80)

        tracker.record(report)
        markdown = tracker.to_markdown()

        assert "Quality Trend" in markdown
        assert "improving" in markdown or "declining" in markdown


class TestLocalPrecommitChecker:
    """Test local pre-commit verification."""

    @pytest.fixture
    def mock_report(self):
        """Create mock report."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.75)
        report.evaluation_suite.quality_scores = Mock(return_value={
            "m1": 0.75,
            "m2": 0.76,
        })
        return report

    def test_precommit_pass(self, mock_report):
        """Test pre-commit check passing."""
        checker = LocalPrecommitChecker()
        passed, msg = checker.quick_check(mock_report)

        assert passed
        assert "passed" in msg.lower()

    def test_precommit_fail_quality(self):
        """Test pre-commit check failing on quality."""
        report = Mock()
        report.overall_quality = Mock(return_value=0.50)
        report.evaluation_suite.quality_scores = Mock(return_value={"m1": 0.50})

        checker = LocalPrecommitChecker()
        passed, msg = checker.quick_check(report)

        assert not passed
        assert "below minimum" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
