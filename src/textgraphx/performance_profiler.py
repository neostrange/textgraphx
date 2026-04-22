"""M13.1: Phase-Level Performance Profiler.

Instruments each phase to identify bottleneck operations and measure throughput:
  - Execution time per phase (wall-clock, CPU)
  - Graph query performance (Cypher duration, cardinality)
  - Memory/cardinality growth tracking
  - Bottleneck detection and reporting
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json


@dataclass
class QueryMetrics:
    """Metrics for a single Cypher query execution."""
    
    query_name: str
    duration_ms: float
    rows_affected: int = 0
    rows_returned: int = 0
    cardinality_before: Optional[int] = None
    cardinality_after: Optional[int] = None
    query_plan: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def cardinality_delta(self) -> Optional[int]:
        """Return change in graph cardinality (nodes/edges added)."""
        if self.cardinality_before is not None and self.cardinality_after is not None:
            return self.cardinality_after - self.cardinality_before
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_name": self.query_name,
            "duration_ms": self.duration_ms,
            "rows_affected": self.rows_affected,
            "rows_returned": self.rows_returned,
            "cardinality_delta": self.cardinality_delta(),
            "timestamp": self.timestamp,
        }


@dataclass
class PhaseMetrics:
    """Aggregated metrics for a single pipeline phase."""
    
    phase_name: str
    execution_count: int = 0
    total_duration_seconds: float = 0.0
    documents_processed: int = 0
    queries_executed: int = 0
    total_rows_affected: int = 0
    cardinality_delta: int = 0  # Total nodes/edges added
    query_metrics: List[QueryMetrics] = field(default_factory=list)
    peak_cardinality: int = 0
    timestamp_start: Optional[str] = None
    
    def average_duration(self) -> float:
        """Average execution duration per document."""
        if self.documents_processed == 0:
            return 0.0
        return self.total_duration_seconds / self.documents_processed
    
    def throughput(self) -> float:
        """Documents per second."""
        if self.total_duration_seconds <= 0:
            return 0.0
        return self.documents_processed / self.total_duration_seconds
    
    def query_duration_breakdown(self) -> Dict[str, float]:
        """Time spent in each query type."""
        breakdown: Dict[str, float] = {}
        for qm in self.query_metrics:
            if qm.query_name not in breakdown:
                breakdown[qm.query_name] = 0.0
            breakdown[qm.query_name] += qm.duration_ms / 1000.0
        return breakdown
    
    def slowest_queries(self, top_n: int = 5) -> List[QueryMetrics]:
        """Return slowest queries by duration."""
        return sorted(self.query_metrics, key=lambda q: q.duration_ms, reverse=True)[:top_n]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "execution_count": self.execution_count,
            "total_duration_seconds": self.total_duration_seconds,
            "average_duration_per_doc": self.average_duration(),
            "throughput_docs_per_sec": self.throughput(),
            "documents_processed": self.documents_processed,
            "queries_executed": self.queries_executed,
            "total_rows_affected": self.total_rows_affected,
            "cardinality_delta": self.cardinality_delta,
            "peak_cardinality": self.peak_cardinality,
            "slowest_queries": [q.to_dict() for q in self.slowest_queries()],
        }


class PhaseProfiler:
    """Profiles phase execution for bottleneck identification."""
    
    def __init__(self):
        """Initialize phase profiler."""
        self.phase_metrics: Dict[str, PhaseMetrics] = {}
        self.active_phase: Optional[str] = None
        self.phase_start_time: Optional[float] = None
        self.phase_cardinality_start: Optional[int] = None
    
    def start_phase(self, phase_name: str, graph: Optional[Any] = None, doc_count: int = 1) -> None:
        """Start profiling a phase."""
        self.active_phase = phase_name
        self.phase_start_time = time.time()
        
        # Capture initial cardinality
        if graph is not None:
            try:
                result = graph.run("MATCH () RETURN count(*) AS c").data()
                self.phase_cardinality_start = int(result[0]["c"]) if result else 0
            except Exception:
                self.phase_cardinality_start = None
        
        # Initialize phase metrics if not present
        if phase_name not in self.phase_metrics:
            self.phase_metrics[phase_name] = PhaseMetrics(
                phase_name=phase_name,
                timestamp_start=datetime.now(timezone.utc).isoformat(),
            )
        
        metrics = self.phase_metrics[phase_name]
        metrics.execution_count += 1
        metrics.documents_processed += doc_count
    
    def record_query(
        self,
        query_name: str,
        duration_ms: float,
        rows_affected: int = 0,
        rows_returned: int = 0,
    ) -> None:
        """Record a query execution within active phase."""
        if self.active_phase is None:
            return
        
        metrics = self.phase_metrics[self.active_phase]
        qm = QueryMetrics(
            query_name=query_name,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            rows_returned=rows_returned,
        )
        metrics.query_metrics.append(qm)
        metrics.queries_executed += 1
        metrics.total_rows_affected += rows_affected
    
    def end_phase(self, graph: Optional[Any] = None) -> PhaseMetrics:
        """End profiling for active phase."""
        if self.active_phase is None or self.phase_start_time is None:
            raise RuntimeError("No active phase to end")
        
        elapsed = time.time() - self.phase_start_time
        metrics = self.phase_metrics[self.active_phase]
        metrics.total_duration_seconds += elapsed
        
        # Capture final cardinality
        if graph is not None and self.phase_cardinality_start is not None:
            try:
                result = graph.run("MATCH () RETURN count(*) AS c").data()
                cardinality_end = int(result[0]["c"]) if result else 0
                metrics.cardinality_delta += cardinality_end - self.phase_cardinality_start
                metrics.peak_cardinality = max(metrics.peak_cardinality, cardinality_end)
            except Exception:
                pass
        
        self.active_phase = None
        self.phase_start_time = None
        self.phase_cardinality_start = None
        
        return metrics
    
    def get_phase_metrics(self, phase_name: str) -> Optional[PhaseMetrics]:
        """Retrieve metrics for a specific phase."""
        return self.phase_metrics.get(phase_name)
    
    def get_slowest_phases(self, top_n: int = 5) -> List[PhaseMetrics]:
        """Return phases sorted by total execution time."""
        phases = list(self.phase_metrics.values())
        return sorted(phases, key=lambda p: p.total_duration_seconds, reverse=True)[:top_n]
    
    def get_bottleneck_report(self) -> Dict[str, Any]:
        """Generate bottleneck detection report."""
        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": [],
            "bottlenecks": [],
            "recommendations": [],
        }
        
        for phase_metrics in self.get_slowest_phases(top_n=10):
            report["phases"].append(phase_metrics.to_dict())
            
            # Identify slow queries within phase
            slowest = phase_metrics.slowest_queries(top_n=3)
            for query in slowest:
                if query.duration_ms > 1000:  # > 1 second is a bottleneck
                    report["bottlenecks"].append({
                        "phase": phase_metrics.phase_name,
                        "query": query.query_name,
                        "duration_ms": query.duration_ms,
                        "severity": "critical" if query.duration_ms > 5000 else "high",
                    })
            
            # Generate phase-level recommendations
            if phase_metrics.average_duration() > 10.0:  # > 10s per doc is slow
                report["recommendations"].append({
                    "phase": phase_metrics.phase_name,
                    "issue": f"High average duration: {phase_metrics.average_duration():.2f}s per document",
                    "action": "Profile and optimize Cypher queries; consider parallelization",
                })
            
            if phase_metrics.cardinality_delta > 100000:  # Large output growth
                report["recommendations"].append({
                    "phase": phase_metrics.phase_name,
                    "issue": f"High cardinality growth: +{phase_metrics.cardinality_delta} nodes/edges",
                    "action": "Check for combinatorial explosion in fusion/matching logic",
                })
        
        return report
    
    def to_json(self) -> str:
        """Serialize all metrics to JSON."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                name: metrics.to_dict()
                for name, metrics in self.phase_metrics.items()
            },
            "bottleneck_report": self.get_bottleneck_report(),
        }
        return json.dumps(data, indent=2)
    
    def reset(self) -> None:
        """Clear all recorded metrics."""
        self.phase_metrics.clear()
        self.active_phase = None
        self.phase_start_time = None
        self.phase_cardinality_start = None


# Global profiler instance
_global_profiler = PhaseProfiler()


def get_profiler() -> PhaseProfiler:
    """Get the global phase profiler instance."""
    return _global_profiler
