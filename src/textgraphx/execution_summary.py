"""Compatibility wrapper for the canonical runtime summary module in orchestration."""

from textgraphx.orchestration.runtime_summary import (
    ExecutionSummary,
    PhaseMetrics,
    print_phase_progress,
)

__all__ = ["ExecutionSummary", "PhaseMetrics", "print_phase_progress"]
