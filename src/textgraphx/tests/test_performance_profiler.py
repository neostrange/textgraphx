"""M13: Performance Profiling Tests.

Unit tests for phase profiler, bottleneck detection, and performance metrics.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest

from textgraphx.infrastructure.performance_profiler import (
    QueryMetrics, PhaseMetrics, PhaseProfiler, get_profiler
)


class TestQueryMetrics:
    """Unit tests for QueryMetrics."""
    
    def test_query_metrics_initialization(self):
        """Test QueryMetrics creation."""
        qm = QueryMetrics(
            query_name="match_entities",
            duration_ms=245.5,
            rows_affected=15,
            rows_returned=15,
        )
        
        assert qm.query_name == "match_entities"
        assert qm.duration_ms == 245.5
        assert qm.rows_affected == 15
        assert qm.cardinality_delta() is None
    
    def test_query_metrics_cardinality_delta(self):
        """Test cardinality delta calculation."""
        qm = QueryMetrics(
            query_name="create_edges",
            duration_ms=100.0,
            cardinality_before=1000,
            cardinality_after=1050,
        )
        
        assert qm.cardinality_delta() == 50
    
    def test_query_metrics_to_dict(self):
        """Test QueryMetrics serialization."""
        qm = QueryMetrics(
            query_name="test_query",
            duration_ms=150.0,
            rows_affected=5,
            cardinality_before=100,
            cardinality_after=110,
        )
        
        d = qm.to_dict()
        assert d["query_name"] == "test_query"
        assert d["duration_ms"] == 150.0
        assert d["cardinality_delta"] == 10


class TestPhaseMetrics:
    """Unit tests for PhaseMetrics."""
    
    def test_phase_metrics_initialization(self):
        """Test PhaseMetrics creation."""
        pm = PhaseMetrics(
            phase_name="temporal_phase",
            execution_count=2,
            documents_processed=5,
        )
        
        assert pm.phase_name == "temporal_phase"
        assert pm.execution_count == 2
        assert pm.documents_processed == 5
    
    def test_average_duration_calculation(self):
        """Test average duration per document."""
        pm = PhaseMetrics(
            phase_name="test_phase",
            total_duration_seconds=10.0,
            documents_processed=5,
        )
        
        assert pm.average_duration() == 2.0
    
    def test_average_duration_zero_docs(self):
        """Test average duration with zero documents."""
        pm = PhaseMetrics(
            phase_name="test_phase",
            total_duration_seconds=10.0,
            documents_processed=0,
        )
        
        assert pm.average_duration() == 0.0
    
    def test_throughput_calculation(self):
        """Test throughput (docs per second)."""
        pm = PhaseMetrics(
            phase_name="test_phase",
            total_duration_seconds=5.0,
            documents_processed=20,
        )
        
        assert pm.throughput() == 4.0  # 20 docs / 5 sec = 4 docs/sec
    
    def test_query_duration_breakdown(self):
        """Test query time breakdown by query name."""
        pm = PhaseMetrics(phase_name="test_phase")
        pm.query_metrics = [
            QueryMetrics("query_a", 100.0),
            QueryMetrics("query_a", 150.0),
            QueryMetrics("query_b", 50.0),
        ]
        
        breakdown = pm.query_duration_breakdown()
        # 100ms + 150ms = 250ms = 0.25s for query_a
        assert abs(breakdown["query_a"] - 0.25) < 0.001
        # 50ms = 0.05s for query_b
        assert abs(breakdown["query_b"] - 0.05) < 0.001
    
    def test_slowest_queries(self):
        """Test ranking of slowest queries."""
        pm = PhaseMetrics(phase_name="test_phase")
        pm.query_metrics = [
            QueryMetrics("query_a", 100.0),
            QueryMetrics("query_b", 500.0),
            QueryMetrics("query_c", 300.0),
        ]
        
        slowest = pm.slowest_queries(top_n=2)
        assert len(slowest) == 2
        assert slowest[0].query_name == "query_b"
        assert slowest[1].query_name == "query_c"
    
    def test_phase_metrics_to_dict(self):
        """Test PhaseMetrics serialization."""
        pm = PhaseMetrics(
            phase_name="test_phase",
            execution_count=3,
            total_duration_seconds=15.0,
            documents_processed=10,
            queries_executed=25,
            cardinality_delta=500,
        )
        
        d = pm.to_dict()
        assert d["phase_name"] == "test_phase"
        assert d["execution_count"] == 3
        assert d["total_duration_seconds"] == 15.0
        assert d["average_duration_per_doc"] == 1.5
        assert d["throughput_docs_per_sec"] == pytest.approx(0.667, rel=0.01)


class TestPhaseProfiler:
    """Unit tests for PhaseProfiler."""
    
    def test_profiler_initialization(self):
        """Test PhaseProfiler creation."""
        profiler = PhaseProfiler()
        
        assert profiler.active_phase is None
        assert profiler.phase_start_time is None
        assert len(profiler.phase_metrics) == 0
    
    def test_start_and_end_phase(self):
        """Test starting and ending a phase."""
        profiler = PhaseProfiler()
        mock_graph = MagicMock()
        mock_graph.run.return_value.data.return_value = [{"c": 1000}]
        
        profiler.start_phase("temporal_phase", graph=mock_graph, doc_count=3)
        assert profiler.active_phase == "temporal_phase"
        
        metrics = profiler.end_phase(graph=mock_graph)
        assert metrics.phase_name == "temporal_phase"
        assert metrics.documents_processed == 3
        assert profiler.active_phase is None
    
    def test_record_query(self):
        """Test recording query metrics."""
        profiler = PhaseProfiler()
        
        profiler.start_phase("test_phase", doc_count=1)
        profiler.record_query("query_a", duration_ms=100.0, rows_affected=5)
        profiler.record_query("query_b", duration_ms=200.0, rows_affected=10)
        metrics = profiler.end_phase()
        
        assert metrics.queries_executed == 2
        assert metrics.total_rows_affected == 15
        assert len(metrics.query_metrics) == 2
    
    def test_get_phase_metrics(self):
        """Test retrieving phase metrics."""
        profiler = PhaseProfiler()
        
        profiler.start_phase("phase_1", doc_count=5)
        profiler.end_phase()
        
        metrics = profiler.get_phase_metrics("phase_1")
        assert metrics is not None
        assert metrics.phase_name == "phase_1"
        assert metrics.documents_processed == 5
    
    def test_get_slowest_phases(self):
        """Test identifying slowest phases."""
        profiler = PhaseProfiler()
        
        # Simulate multiple phases with different durations
        profiler.start_phase("phase_a", doc_count=1)
        profiler.phase_metrics["phase_a"].total_duration_seconds = 5.0
        profiler.phase_metrics["phase_a"].execution_count = 1
        
        profiler.start_phase("phase_b", doc_count=1)
        profiler.phase_metrics["phase_b"].total_duration_seconds = 15.0
        profiler.phase_metrics["phase_b"].execution_count = 1
        
        slowest = profiler.get_slowest_phases(top_n=2)
        assert len(slowest) == 2
        assert slowest[0].phase_name == "phase_b"
        assert slowest[1].phase_name == "phase_a"
    
    def test_bottleneck_report_generation(self):
        """Test bottleneck detection report."""
        profiler = PhaseProfiler()
        
        profiler.start_phase("slow_phase", doc_count=10)
        profiler.record_query("slow_query", duration_ms=2000.0, rows_affected=100)
        profiler.record_query("fast_query", duration_ms=50.0, rows_affected=10)
        profiler.phase_metrics["slow_phase"].cardinality_delta = 150000
        profiler.end_phase()
        
        report = profiler.get_bottleneck_report()
        
        assert "bottlenecks" in report
        assert "recommendations" in report
        # Slow query should be in bottlenecks
        assert any(b["duration_ms"] == 2000.0 for b in report["bottlenecks"])
        # High cardinality growth should trigger recommendation
        assert any("cardinality" in r["issue"].lower() for r in report["recommendations"])
    
    def test_profiler_to_json(self):
        """Test JSON serialization."""
        profiler = PhaseProfiler()
        
        profiler.start_phase("test_phase", doc_count=5)
        profiler.record_query("test_query", duration_ms=100.0)
        profiler.end_phase()
        
        json_str = profiler.to_json()
        data = json.loads(json_str)
        
        assert "metrics" in data
        assert "test_phase" in data["metrics"]
        assert data["metrics"]["test_phase"]["documents_processed"] == 5
    
    def test_profiler_reset(self):
        """Test clearing profiler state."""
        profiler = PhaseProfiler()
        
        profiler.start_phase("phase_1", doc_count=5)
        profiler.end_phase()
        
        assert len(profiler.phase_metrics) > 0
        
        profiler.reset()
        assert len(profiler.phase_metrics) == 0
        assert profiler.active_phase is None
    
    def test_multiple_phase_executions(self):
        """Test profiling multiple executions of same phase."""
        profiler = PhaseProfiler()
        
        # Run phase A twice
        for run in range(2):
            profiler.start_phase("phase_a", doc_count=3)
            profiler.record_query("query", duration_ms=100.0, rows_affected=5)
            profiler.end_phase()
        
        metrics = profiler.get_phase_metrics("phase_a")
        assert metrics.execution_count == 2
        assert metrics.documents_processed == 6
        assert metrics.queries_executed == 2
        assert metrics.total_rows_affected == 10


class TestGlobalProfilerInstance:
    """Tests for the global profiler singleton."""
    
    def test_get_global_profiler(self):
        """Test retrieving global profiler instance."""
        profiler = get_profiler()
        assert isinstance(profiler, PhaseProfiler)
    
    def test_profiler_singleton_behavior(self):
        """Test that global profiler maintains state across calls."""
        profiler1 = get_profiler()
        profiler2 = get_profiler()
        
        # Should be the same instance
        assert profiler1 is profiler2
