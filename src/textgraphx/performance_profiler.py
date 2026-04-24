"""Compatibility wrapper for the canonical infrastructure performance-profiler module."""

from textgraphx.infrastructure.performance_profiler import (
    PhaseMetrics,
    PhaseProfiler,
    QueryMetrics,
    get_profiler,
)

__all__ = [
    "PhaseMetrics",
    "PhaseProfiler",
    "QueryMetrics",
    "get_profiler",
]
import json
