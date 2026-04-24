"""Runtime tests for textgraphx/execution_history.py timestamp behavior."""

from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import sqlite3  # noqa: F401
except ModuleNotFoundError:
    pytest.skip("sqlite3 module is unavailable in this Python environment", allow_module_level=True)

from textgraphx.execution_history import ExecutionRecord
from textgraphx.orchestration.runtime_history import ExecutionRecord as CanonicalExecutionRecord


@pytest.mark.unit
class TestExecutionHistoryTimestampBehavior:
    def test_root_execution_history_wrapper_reexports_canonical_record(self):
        assert ExecutionRecord is CanonicalExecutionRecord

    def test_default_started_and_completed_are_timezone_aware_utc(self):
        record = ExecutionRecord(
            execution_id="exec-1",
            dataset_path="/tmp/dataset",
            phases="ingestion,refinement",
            status="success",
            total_duration=1.23,
            phase_timings={"ingestion": 0.5, "refinement": 0.73},
            documents_processed=3,
        )

        started = datetime.fromisoformat(record.started_at)
        completed = datetime.fromisoformat(record.completed_at)

        assert started.tzinfo is not None
        assert completed.tzinfo is not None
        assert started.utcoffset() == timedelta(0)
        assert completed.utcoffset() == timedelta(0)

    def test_explicit_timestamps_are_preserved(self):
        custom_started = "2026-01-01T00:00:00"
        custom_completed = "2026-01-01T00:00:05"

        record = ExecutionRecord(
            execution_id="exec-2",
            dataset_path="/tmp/dataset",
            phases="ingestion",
            status="success",
            total_duration=5.0,
            phase_timings={"ingestion": 5.0},
            documents_processed=1,
            started_at=custom_started,
            completed_at=custom_completed,
        )

        assert record.started_at == custom_started
        assert record.completed_at == custom_completed
