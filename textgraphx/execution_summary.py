"""
Execution summary and metrics tracking for TextGraphX pipeline.
Provides formatted output of pipeline execution results and performance data.
"""

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import time


@dataclass
class PhaseMetrics:
    """Metrics for a single phase execution."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    steps_completed: int = 0
    total_steps: Optional[int] = None

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time

    def complete(self, steps: int = 0) -> None:
        """Mark phase as completed."""
        self.end_time = time.perf_counter()
        self.status = "completed"
        self.steps_completed = steps

    def fail(self, error: str) -> None:
        """Mark phase as failed."""
        self.end_time = time.perf_counter()
        self.status = "failed"
        self.error = error


class ExecutionSummary:
    """Tracks and reports pipeline execution summary."""

    def __init__(self) -> None:
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.phases: Dict[str, PhaseMetrics] = {}
        self.total_documents: int = 0
        self.errors: List[str] = []

    def start(self) -> None:
        """Mark execution start."""
        self.start_time = time.perf_counter()

    def finish(self) -> None:
        """Mark execution end."""
        self.end_time = time.perf_counter()

    def start_phase(self, phase_name: str) -> None:
        """Start tracking a phase."""
        self.phases[phase_name] = PhaseMetrics(
            name=phase_name,
            start_time=time.perf_counter()
        )

    def complete_phase(self, phase_name: str, steps: int = 0) -> None:
        """Mark a phase as completed."""
        if phase_name in self.phases:
            self.phases[phase_name].complete(steps)

    def fail_phase(self, phase_name: str, error: str) -> None:
        """Mark a phase as failed."""
        if phase_name in self.phases:
            self.phases[phase_name].fail(error)
        self.errors.append(f"{phase_name}: {error}")

    def set_documents_processed(self, count: int) -> None:
        """Set the number of documents processed."""
        self.total_documents = count

    @property
    def total_duration(self) -> float:
        """Total execution duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def phase_count(self) -> int:
        """Number of phases executed."""
        return len(self.phases)

    @property
    def success_count(self) -> int:
        """Number of completed phases."""
        return sum(1 for p in self.phases.values() if p.status == "completed")

    @property
    def failed_count(self) -> int:
        """Number of failed phases."""
        return sum(1 for p in self.phases.values() if p.status == "failed")

    def format_summary(self) -> str:
        """Format execution summary as human-readable string."""
        if not self.phases:
            return "No phases executed."

        lines = []
        lines.append("=" * 70)
        lines.append("📊 Execution Summary")
        lines.append("=" * 70)

        # Overall status
        if self.failed_count == 0 and self.success_count > 0:
            status = "✅ SUCCESS"
        elif self.failed_count > 0:
            status = "❌ FAILED"
        else:
            status = "⚠️  INCOMPLETE"

        lines.append(f"Status:     {status}")
        lines.append(f"Duration:   {self._format_duration(self.total_duration)}")
        lines.append(f"Phases:     {self.success_count}/{self.phase_count} completed")

        if self.total_documents > 0:
            lines.append(f"Documents:  {self.total_documents} processed")

        lines.append("")
        lines.append("Phase Details:")
        lines.append("-" * 70)

        # Phase breakdown
        for phase_name in ["ingestion", "refinement", "temporal", "event_enrichment", "tlinks"]:
            if phase_name in self.phases:
                phase = self.phases[phase_name]
                duration_str = self._format_duration(phase.duration)
                
                if phase.status == "completed":
                    status_icon = "✅"
                elif phase.status == "failed":
                    status_icon = "❌"
                else:
                    status_icon = "⏳"
                
                lines.append(f"  {status_icon} {phase.name:20s} {duration_str:>10s}")

                if phase.error:
                    lines.append(f"     Error: {phase.error}")

        if self.errors:
            lines.append("")
            lines.append("Errors:")
            lines.append("-" * 70)
            for error in self.errors:
                lines.append(f"  • {error}")

        lines.append("=" * 70)

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print formatted summary to stdout."""
        print("\n" + self.format_summary() + "\n")

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = seconds / 60
            return f"{minutes:.1f}m"


def print_phase_progress(current_phase: str, phase_index: int, total_phases: int) -> None:
    """Print current phase progress indicator."""
    progress = f"[{phase_index}/{total_phases}]"
    print(f"\n{progress} Running phase: {current_phase}...")


if __name__ == "__main__":
    # Test example
    summary = ExecutionSummary()
    summary.start()

    # Simulate phases
    for phase in ["ingestion", "refinement", "temporal"]:
        summary.start_phase(phase)
        time.sleep(0.1)
        summary.complete_phase(phase, steps=10)

    summary.set_documents_processed(42)
    summary.finish()

    summary.print_summary()
