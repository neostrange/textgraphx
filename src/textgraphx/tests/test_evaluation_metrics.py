"""Unit and regression tests for Iteration 4 evaluation metrics harness."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
class TestPrimitiveMetrics:
    def test_safe_division_handles_zero_denominator(self):
        from textgraphx.evaluation.metrics import _safe_div

        assert _safe_div(10, 0) == 0.0

    def test_precision_recall_f1_basic(self):
        from textgraphx.evaluation.metrics import precision_recall_f1

        m = precision_recall_f1(tp=8, fp=2, fn=4)
        assert m["precision"] == pytest.approx(0.8)
        assert m["recall"] == pytest.approx(8 / 12)
        assert m["f1"] == pytest.approx(2 * 0.8 * (8 / 12) / (0.8 + (8 / 12)))

    def test_precision_recall_f1_all_zero(self):
        from textgraphx.evaluation.metrics import precision_recall_f1

        m = precision_recall_f1(tp=0, fp=0, fn=0)
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0

    def test_coverage(self):
        from textgraphx.evaluation.metrics import coverage

        assert coverage(processed=75, total=100) == pytest.approx(0.75)

    def test_coverage_zero_total(self):
        from textgraphx.evaluation.metrics import coverage

        assert coverage(processed=5, total=0) == 0.0


@pytest.mark.unit
class TestAggregateMetrics:
    def test_macro_average(self):
        from textgraphx.evaluation.metrics import macro_average

        rows = [{"f1": 0.5}, {"f1": 1.0}, {"f1": 0.0}]
        assert macro_average(rows, "f1") == pytest.approx(0.5)

    def test_macro_average_empty(self):
        from textgraphx.evaluation.metrics import macro_average

        assert macro_average([], "f1") == 0.0

    def test_quality_report_structure(self):
        from textgraphx.evaluation.metrics import build_quality_report

        report = build_quality_report(
            "entity",
            tp=10,
            fp=5,
            fn=5,
            processed=80,
            total=100,
        )
        assert report["dimension"] == "entity"
        assert "metrics" in report
        assert "coverage" in report


@pytest.mark.regression
class TestMetricsContract:
    """Lock the public API shape used by higher-level tools and CI."""

    def test_precision_recall_f1_keys_stable(self):
        from textgraphx.evaluation.metrics import precision_recall_f1

        keys = set(precision_recall_f1(1, 0, 0).keys())
        assert keys == {"tp", "fp", "fn", "precision", "recall", "f1"}

    def test_build_quality_report_keys_stable(self):
        from textgraphx.evaluation.metrics import build_quality_report

        report = build_quality_report("temporal", 1, 1, 1, 1, 2)
        assert set(report.keys()) == {"dimension", "metrics", "coverage"}
        assert set(report["coverage"].keys()) == {"processed", "total", "coverage"}
