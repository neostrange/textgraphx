"""Tests for Milestones 2-7: Phase evaluators and full-stack harness.

Tests cover:
- Mention layer evaluation (M2)
- Edge semantics evaluation (M3)
- Phase assertions validation (M4)
- Semantic category evaluation (M5)
- Legacy layer evaluation (M6)
- Full-stack orchestration (M7)
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest

from textgraphx.evaluation import (
    EdgeSemanticsEvaluator,
    EvaluationSuite,
    FullStackEvaluator,
    LegacyLayerEvaluator,
    MentionLayerEvaluator,
    PhaseAssertionEvaluator,
    RunMetadata,
    SemanticCategoryEvaluator,
    create_edge_semantics_report,
    create_legacy_layer_report,
    create_mention_layer_report,
    create_phase_assertion_report,
    create_semantic_category_report,
)


class MockGraph:
    """Mock Neo4j graph for testing."""

    def __init__(self, metrics_dict=None):
        self.metrics = metrics_dict or {}

    def run(self, query: str, params=None):
        """Mock query execution."""
        # Return mock results based on query
        # Handle both 'c' and named return columns
        result = MagicMock()
        
        if "em_count" in query:
            result.data.return_value = [{"em_count": 0}]
        elif "tm_count" in query:
            result.data.return_value = [{"tm_count": 0}]
        elif "dual_count" in query:
            result.data.return_value = [{"dual_count": 0}]
        else:
            count = self.metrics.get(query, 0)
            result.data.return_value = [{"c": count}]
        return result


class TestMentionLayerEvaluator:
    """Tests for Milestone 2: Mention Layer."""

    def test_mention_layer_evaluation(self):
        """Test basic mention layer metrics computation."""
        mock_graph = MockGraph(
            {
                "MATCH (n:EntityMention) RETURN count(n) AS c": 100,
                "MATCH (em:EntityMention)-[:REFERS_TO]->(e:Entity) RETURN count(*) AS c": 95,
            }
        )

        evaluator = MentionLayerEvaluator(mock_graph)
        metrics = evaluator.evaluate()

        assert metrics.entity_mentions_created == 100
        assert metrics.entity_mentions_with_refers_to == 95

    def test_mention_layer_quality_score(self):
        """Test mention layer quality score computation."""
        mock_graph = MockGraph({})
        evaluator = MentionLayerEvaluator(mock_graph)
        metrics = evaluator.evaluate()
        
        # Should compute quality score when metrics are 0
        assert 0.0 <= metrics.compute_quality_score() <= 1.0

    def test_create_mention_layer_report(self):
        """Test creating unified report from mention layer evaluation."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        mock_graph = MockGraph({})
        report = create_mention_layer_report(meta, mock_graph)

        assert report.metric_type == "mention_layer_metrics"
        assert report.validity_header.run_metadata.seed == 42


class TestEdgeSemanticsEvaluator:
    """Tests for Milestone 3: Edge Semantics."""

    def test_edge_semantics_evaluation(self):
        """Test edge semantics metrics."""
        mock_graph = MockGraph({})
        evaluator = EdgeSemanticsEvaluator(mock_graph)
        metrics = evaluator.evaluate()

        assert metrics.total_edges == 0
        assert metrics.typed_edges == 0

    def test_create_edge_semantics_report(self):
        """Test unified edge semantics report creation."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=True,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        mock_graph = MockGraph({})
        report = create_edge_semantics_report(meta, mock_graph, determinism_pass=True)

        assert report.metric_type == "edge_semantics_metrics"
        assert report.validity_header.determinism_pass is True


class TestPhaseAssertionEvaluator:
    """Tests for Milestone 4: Phase Assertions."""

    def test_phase_assertion_evaluation(self):
        """Test phase assertion metrics."""
        mock_graph = MockGraph({})
        evaluator = PhaseAssertionEvaluator(mock_graph)
        metrics = evaluator.evaluate()

        assert metrics.total_nodes_checked == 0
        assert metrics.schema_violations == 0

    def test_create_phase_assertion_report(self):
        """Test unified phase assertion report."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        mock_graph = MockGraph({})
        report = create_phase_assertion_report(meta, mock_graph)

        assert report.metric_type == "phase_assertion_metrics"
        assert "phase_materialization_active" in report.validity_header.feature_activation_evidence


class TestSemanticCategoryEvaluator:
    """Tests for Milestone 5: Semantic Categories."""

    def test_semantic_category_evaluation(self):
        """Test semantic category metrics."""
        mock_graph = MockGraph({})
        evaluator = SemanticCategoryEvaluator(mock_graph)
        metrics = evaluator.evaluate()

        assert metrics.total_frames == 0
        assert metrics.frames_with_categories == 0

    def test_create_semantic_category_report(self):
        """Test unified semantic category report."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        mock_graph = MockGraph({})
        report = create_semantic_category_report(meta, mock_graph)

        assert report.metric_type == "semantic_category_metrics"
        assert "semantic_categorization_activated" in report.validity_header.feature_activation_evidence


class TestLegacyLayerEvaluator:
    """Tests for Milestone 6: Legacy Layer."""

    def test_legacy_layer_evaluation(self):
        """Test legacy layer metrics."""
        mock_graph = MockGraph({})
        evaluator = LegacyLayerEvaluator(mock_graph)
        metrics = evaluator.evaluate()

        assert metrics.legacy_nodes_total == 0
        assert metrics.legacy_orphans == 0

    def test_create_legacy_layer_report(self):
        """Test unified legacy layer report."""
        meta = RunMetadata(
            dataset_hash="abc",
            config_hash="xyz",
            seed=42,
            strict_gate_enabled=True,
            fusion_enabled=False,
            cleanup_mode="auto",
            timestamp="2026-04-05T12:00:00Z",
        )

        mock_graph = MockGraph({})
        report = create_legacy_layer_report(meta, mock_graph)

        assert report.metric_type == "legacy_layer_metrics"


class TestFullStackEvaluator:
    """Tests for Milestone 7: Full-Stack Harness."""

    def test_fullstack_evaluator_initialization(self):
        """Test FullStackEvaluator setup."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"model": "test"},
                seed=42,
            )

            assert evaluator.runner.seed == 42

    def test_fullstack_evaluation_suite(self):
        """Test running complete evaluation suite."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()

            assert isinstance(suite, EvaluationSuite)
            assert suite.mention_layer is not None
            assert suite.edge_semantics is not None
            assert suite.phase_assertions is not None
            assert suite.semantic_categories is not None
            assert suite.legacy_layer is not None

    def test_evaluation_suite_quality_scores(self):
        """Test quality score computation."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            scores = suite.quality_scores()

            assert "mention_layer" in scores
            assert "edge_semantics" in scores
            assert "phase_assertions" in scores
            assert "semantic_categories" in scores
            assert "legacy_layer" in scores

    def test_evaluation_suite_conclusiveness(self):
        """Test conclusiveness check."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            conclusive, reasons = suite.conclusiveness()

            # With mock data, might be inconclusive
            assert isinstance(conclusive, bool)
            assert isinstance(reasons, list)

    def test_fullstack_json_export(self):
        """Test JSON export of evaluation suite."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            export_path = tmp / "eval.json"
            evaluator.export_json(suite, export_path)

            assert export_path.exists()
            with open(export_path) as f:
                data = json.load(f)
            assert "run_metadata" in data
            assert "quality_scores" in data
            assert "reports" in data

    def test_fullstack_markdown_export(self):
        """Test markdown export."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            export_path = tmp / "eval.md"
            evaluator.export_markdown(suite, export_path)

            assert export_path.exists()
            content = export_path.read_text()
            assert "Full-Stack Evaluation Report" in content
            assert "Quality Scores by Phase" in content

    def test_fullstack_csv_export(self):
        """Test CSV export."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            export_path = tmp / "eval.csv"
            evaluator.export_csv(suite, export_path)

            assert export_path.exists()
            content = export_path.read_text()
            assert "metric_type" in content


class TestComparisonAndConsistency:
    """Tests for determinism and suite comparison."""

    def test_evaluation_suite_to_dict(self):
        """Test suite serialization."""
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "gold.json").write_text("{}")

            mock_graph = MockGraph({})

            evaluator = FullStackEvaluator(
                graph=mock_graph,
                dataset_paths=list(tmp.glob("*.json")),
                config_dict={"x": 1},
            )

            suite = evaluator.evaluate()
            data = suite.to_dict()

            assert "run_metadata" in data
            assert "execution_time_seconds" in data
            assert "quality_scores" in data
            assert "overall_quality" in data
            assert "conclusiveness" in data
            assert "reports" in data
            assert "runtime_diagnostics" in data
