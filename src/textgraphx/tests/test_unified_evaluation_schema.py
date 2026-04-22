"""Unit tests for unified evaluation schema and validity headers.

Tests cover:
- Validity header creation and serialization
- RunMetadata hashing and serialization
- Determinism checking
- Report creation and export
- Feature activation detection
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from textgraphx.evaluation.determinism import compare_metric_results
from textgraphx.evaluation.integration import (
    StandardizedEvaluationRunner,
    compare_runs_for_determinism,
    load_evaluation_report,
)
from textgraphx.evaluation.report_validity import (
    RunMetadata,
    ValidityHeader,
    check_fusion_activation,
    compute_config_hash,
    compute_dataset_hash,
    render_validity_header_json,
    render_validity_header_yaml,
)
from textgraphx.evaluation.unified_metrics import UnifiedMetricReport, create_unified_report


class TestRunMetadata:
    """Tests for RunMetadata dataclass."""

    def test_run_metadata_creation(self):
        """Test basic RunMetadata instantiation."""
        meta = RunMetadata(
            dataset_hash="abc123",
            config_hash="xyz789",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        assert meta.dataset_hash == "abc123"
        assert meta.seed == 42
        assert meta.fusion_enabled is False

    def test_run_metadata_serialization(self):
        """Test RunMetadata to/from dict."""
        meta = RunMetadata(
            dataset_hash="abc123",
            config_hash="xyz789",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
            duration_seconds=123.45,
        )
        d = meta.to_dict()
        assert d["dataset_hash"] == "abc123"
        assert d["duration_seconds"] == 123.45

        meta2 = RunMetadata.from_dict(d)
        assert meta2.seed == meta.seed


class TestValidityHeader:
    """Tests for ValidityHeader and rendering."""

    def test_validity_header_creation(self):
        """Test creating a validity header."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        header = ValidityHeader(
            run_metadata=meta,
            determinism_checked=True,
            determinism_pass=True,
        )
        assert header.determinism_pass is True
        assert len(header.inconclusive_reasons) == 0

    def test_validity_header_with_inconclusive_reasons(self):
        """Test validity header with inconclusive markers."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=True,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        header = ValidityHeader(
            run_metadata=meta,
            inconclusive_reasons=["fusion_enabled=true but SAME_AS edges created=0"],
        )
        assert not header.to_dict()["is_conclusive"]

    def test_render_validity_header_yaml(self):
        """Test YAML frontmatter rendering."""
        meta = RunMetadata(
            dataset_hash="abc123",
            config_hash="xyz789",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        header = ValidityHeader(run_metadata=meta)
        yaml = render_validity_header_yaml(header)

        assert yaml.startswith("---")
        assert yaml.endswith("---")
        assert "dataset_hash: abc123" in yaml
        assert "seed: 42" in yaml

    def test_render_validity_header_json(self):
        """Test JSON rendering."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        header = ValidityHeader(run_metadata=meta)
        json_data = render_validity_header_json(header)

        assert "validity_header" in json_data
        assert json_data["validity_header"]["run_metadata"]["seed"] == 42


class TestDatasetConfigHashing:
    """Tests for hashing dataset and config."""

    def test_compute_dataset_hash(self):
        """Test deterministic dataset hashing."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "file1.txt").write_text("content1")
            (tmp / "file2.txt").write_text("content2")

            files = sorted(tmp.glob("*.txt"))
            hash1 = compute_dataset_hash(files)
            hash2 = compute_dataset_hash(files)

            assert hash1 == hash2
            assert len(hash1) == 16  # Truncated to 16 chars

    def test_compute_dataset_hash_order_invariant(self):
        """Test that dataset hash is order-independent."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "a.txt").write_text("x")
            (tmp / "b.txt").write_text("y")

            files1 = sorted(tmp.glob("*.txt"))
            files2 = sorted(tmp.glob("*.txt"), reverse=True)

            # Hashes should be same despite file order (because compute_dataset_hash sorts them)
            hash1 = compute_dataset_hash(files1)
            hash2 = compute_dataset_hash(files2)
            assert hash1 == hash2

    def test_compute_config_hash(self):
        """Test deterministic config hashing."""
        config1 = {"seed": 42, "fusion": True, "gate": "strict"}
        config2 = {"gate": "strict", "seed": 42, "fusion": True}  # Different order

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 == hash2  # Key-order independent


class TestDeterminismChecking:
    """Tests for determinism validation."""

    def test_deterministic_comparison(self):
        """Test detecting deterministic runs."""
        results1 = {"precision": 0.85, "recall": 0.90, "f1": 0.875}
        results2 = {"precision": 0.85, "recall": 0.90, "f1": 0.875}

        report = compare_metric_results(results1, results2)
        assert report.conclusive is True
        assert report.num_violations == 0

    def test_non_deterministic_comparison(self):
        """Test detecting differences."""
        results1 = {"precision": 0.85, "recall": 0.90}
        results2 = {"precision": 0.84, "recall": 0.90}

        report = compare_metric_results(results1, results2)
        assert report.conclusive is False
        assert report.num_violations == 1
        assert "precision" in report.violations[0].metric_name

    def test_determinism_with_tolerance(self):
        """Test tolerance in numeric comparisons."""
        results1 = {"precision": 0.85}
        results2 = {"precision": 0.851}

        # Without tolerance: different
        report_strict = compare_metric_results(results1, results2, tolerance=0.0)
        assert report_strict.conclusive is False

        # With 2% tolerance: same
        report_tolerant = compare_metric_results(results1, results2, tolerance=0.02)
        assert report_tolerant.conclusive is True

    def test_missing_keys_are_violations(self):
        """Missing keys in one result should be violations."""
        results1 = {"precision": 0.85, "recall": 0.90}
        results2 = {"precision": 0.85}

        report = compare_metric_results(results1, results2)
        assert report.conclusive is False
        assert report.num_violations == 1


class TestFusionActivationDetection:
    """Tests for detecting feature activation."""

    def test_fusion_activated(self):
        """Test when fusion clearly activated."""
        conclusive, reasons = check_fusion_activation(
            fusion_enabled=True,
            same_as_count=42,
            co_occurs_count=15,
        )
        assert conclusive is True
        assert len(reasons) == 0

    def test_fusion_disabled_but_edges_created(self):
        """Test fusion disabled but edges were somehow created."""
        conclusive, reasons = check_fusion_activation(
            fusion_enabled=False,
            same_as_count=5,
            co_occurs_count=3,
        )
        # Not inconclusive: fusion was disabled, edges are unexpected but run is still valid
        assert conclusive is True

    def test_fusion_enabled_but_no_edges(self):
        """Test inconclusive case: fusion enabled but no edges created."""
        conclusive, reasons = check_fusion_activation(
            fusion_enabled=True,
            same_as_count=0,
            co_occurs_count=0,
        )
        assert conclusive is False
        assert len(reasons) > 0
        assert "fusion_enabled=True" in reasons[0]


class TestUnifiedMetricReport:
    """Tests for UnifiedMetricReport."""

    def test_create_unified_report(self):
        """Test creating a unified report."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        report = create_unified_report(
            metric_type="edge_metrics",
            metrics={"precision": 0.85, "recall": 0.90},
            run_metadata=meta,
            determinism_pass=True,
        )

        assert report.metric_type == "edge_metrics"
        assert report.metrics["precision"] == 0.85
        assert report.validity_header.determinism_pass is True

    def test_unified_report_serialization(self):
        """Test report to_dict."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        report = create_unified_report(
            metric_type="mention_metrics",
            metrics={"count": 100},
            run_metadata=meta,
        )

        d = report.to_dict()
        assert d["metric_type"] == "mention_metrics"
        assert d["metrics"]["count"] == 100
        assert "validity_header" in d

    def test_unified_report_json_export(self):
        """Test exporting report to JSON file."""
        with TemporaryDirectory() as tmpdir:
            meta = RunMetadata(
                dataset_hash="abc",
                config_hash="xyz",
                seed=42,
                strict_gate_enabled=True,
                fusion_enabled=False,
                cleanup_mode="auto",
                timestamp="2026-04-05T12:00:00Z",
            )
            report = create_unified_report(
                metric_type="test_metrics",
                metrics={"value": 99},
                run_metadata=meta,
            )

            path = Path(tmpdir) / "report.json"
            report.to_json_file(path)

            assert path.exists()
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["metrics"]["value"] == 99


class TestStandardizedEvaluationRunner:
    """Tests for StandardizedEvaluationRunner."""

    def test_runner_initialization(self):
        """Test creating a runner."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            dataset_file = tmp / "gold.json"
            dataset_file.write_text("{}")

            runner = StandardizedEvaluationRunner(
                dataset_paths=[dataset_file],
                config_dict={"model": "test"},
                seed=42,
                strict_gate_enabled=True,
                fusion_enabled=False,
            )

            assert runner.seed == 42
            assert len(runner.dataset_hash) == 16

    def test_runner_create_run_metadata(self):
        """Test runner creating RunMetadata."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            runner = StandardizedEvaluationRunner(
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
                seed=123,
            )

            start = datetime.now()
            meta = runner.create_run_metadata(start, 45.5)

            assert meta.seed == 123
            assert meta.duration_seconds == 45.5


class TestCompareRunsForDeterminism:
    """Tests for comparing two reports."""

    def test_identical_reports_are_deterministic(self):
        """Test that identical reports pass determinism check."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        report1 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.85},
            run_metadata=meta,
        )
        report2 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.85},
            run_metadata=meta,
        )

        is_det, msgs = compare_runs_for_determinism(report1, report2)
        assert is_det is True
        assert len(msgs) == 0

    def test_different_metrics_are_not_deterministic(self):
        """Test detecting metric differences."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        report1 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.85},
            run_metadata=meta,
        )
        report2 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.84},
            run_metadata=meta,
        )

        is_det, msgs = compare_runs_for_determinism(report1, report2)
        assert is_det is False
        assert len(msgs) > 0

    def test_different_run_parameters_are_not_deterministic(self):
        """Test detecting parameter mismatches."""
        meta1 = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )
        meta2 = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=99,  # Different seed
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        report1 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.85},
            run_metadata=meta1,
        )
        report2 = create_unified_report(
            metric_type="test",
            metrics={"f1": 0.85},
            run_metadata=meta2,
        )

        is_det, msgs = compare_runs_for_determinism(report1, report2)
        assert is_det is False
        assert any("seed" in msg for msg in msgs)


class TestLoadEvaluationReport:
    """Tests for loading saved reports."""

    def test_load_report_roundtrip(self):
        """Test saving and loading a report."""
        with TemporaryDirectory() as tmpdir:
            meta = RunMetadata(
                dataset_hash="abc",
                config_hash="xyz",
                seed=42,
                strict_gate_enabled=True,
                fusion_enabled=False,
                cleanup_mode="auto",
                timestamp="2026-04-05T12:00:00Z",
            )
            report_orig = create_unified_report(
                metric_type="edge_metrics",
                metrics={"p": 0.9, "r": 0.8},
                run_metadata=meta,
                evidence={"edge_types": {"SAME_AS": 10}},
            )

            path = Path(tmpdir) / "report.json"
            report_orig.to_json_file(path)

            report_loaded = load_evaluation_report(path)
            assert report_loaded.metric_type == "edge_metrics"
            assert report_loaded.metrics["p"] == 0.9
            assert report_loaded.validity_header.run_metadata.seed == 42
