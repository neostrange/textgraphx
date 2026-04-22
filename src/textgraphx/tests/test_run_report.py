"""Unit tests for textgraphx/run_report.py.

All tests are pure-Python data-structure tests — no network or DB required.
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.run_report import DocumentStatus, PhaseSummary, RunReport


# ---------------------------------------------------------------------------
# DocumentStatus unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocumentStatus:
    def test_basic_creation(self):
        ds = DocumentStatus(doc_id="d1", filename="a.xml", status="processed")
        assert ds.doc_id == "d1"
        assert ds.status == "processed"
        assert ds.phases_completed == []
        assert ds.failed_phase is None

    def test_failed_status_stores_reason(self):
        ds = DocumentStatus(
            doc_id="d2",
            filename="b.xml",
            status="failed",
            failed_phase="temporal",
            reason="Service unavailable",
        )
        assert ds.failed_phase == "temporal"
        assert ds.reason == "Service unavailable"


# ---------------------------------------------------------------------------
# RunReport unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunReport:
    def test_default_timestamps_are_timezone_aware_utc(self):
        report = RunReport()
        created = datetime.fromisoformat(report.created_at)
        execution = datetime.fromisoformat(report.execution_id)

        assert created.tzinfo is not None
        assert execution.tzinfo is not None
        assert created.utcoffset() == timedelta(0)
        assert execution.utcoffset() == timedelta(0)

    def test_empty_report_has_zero_counts(self):
        report = RunReport()
        assert report.total_count == 0
        assert report.processed_count == 0
        assert report.skipped_count == 0
        assert report.failed_count == 0

    def test_mark_processed_increments_count(self):
        report = RunReport()
        report.mark_processed("doc1", "a.xml", ["ingestion"], duration_seconds=5.0)
        assert report.processed_count == 1
        assert report.total_count == 1
        started = datetime.fromisoformat(report.documents[0].started_at)
        assert started.tzinfo is not None
        assert started.utcoffset() == timedelta(0)

    def test_mark_skipped_increments_count(self):
        report = RunReport()
        report.mark_skipped("doc2", "b.xml", reason="already ingested")
        assert report.skipped_count == 1
        assert report.total_count == 1

    def test_mark_failed_increments_count(self):
        report = RunReport()
        report.mark_failed("doc3", "c.xml", "temporal", reason="timeout")
        assert report.failed_count == 1
        assert report.total_count == 1

    def test_mixed_statuses(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion"])
        report.mark_processed("d2", "b.xml", ["ingestion", "refinement"])
        report.mark_skipped("d3", "c.xml", reason="no text")
        report.mark_failed("d4", "d.xml", "ingestion", "parse error")
        assert report.processed_count == 2
        assert report.skipped_count == 1
        assert report.failed_count == 1
        assert report.total_count == 4

    def test_failed_documents_returns_only_failures(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion"])
        report.mark_failed("d2", "b.xml", "temporal", "error")
        failures = report.failed_documents()
        assert len(failures) == 1
        assert failures[0].doc_id == "d2"

    def test_documents_property_returns_copy(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion"])
        docs = report.documents
        assert len(docs) == 1
        docs.clear()  # mutating the copy should not affect the report
        assert report.total_count == 1

    def test_phase_summary_counts(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion", "refinement"], duration_seconds=10.0)
        report.mark_processed("d2", "b.xml", ["ingestion"], duration_seconds=8.0)
        report.mark_failed("d3", "c.xml", "ingestion", "parse error")
        summary = report.phase_summary()
        assert "ingestion" in summary
        assert summary["ingestion"].documents_attempted == 3
        assert summary["ingestion"].documents_succeeded == 2
        assert summary["ingestion"].documents_failed == 1

    def test_to_dict_is_json_serialisable(self):
        report = RunReport(execution_id="test-exec-1")
        report.mark_processed("d1", "a.xml", ["ingestion"], duration_seconds=5.0)
        report.mark_failed("d2", "b.xml", "temporal", "timeout")
        d = report.to_dict()
        serialized = json.dumps(d)
        assert "test-exec-1" in serialized

    def test_to_dict_contains_expected_keys(self):
        report = RunReport()
        d = report.to_dict()
        assert "execution_id" in d
        assert "summary" in d
        assert "documents" in d
        assert "phase_summary" in d

    def test_to_dict_summary_counts_match(self):
        report = RunReport()
        report.mark_processed("d1", "a.xml", ["ingestion"])
        report.mark_failed("d2", "b.xml", "ingestion", "err")
        d = report.to_dict()
        assert d["summary"]["total"] == 2
        assert d["summary"]["processed"] == 1
        assert d["summary"]["failed"] == 1
        assert d["summary"]["skipped"] == 0

    def test_save_json_creates_file(self):
        report = RunReport(execution_id="exec-save-test")
        report.mark_processed("d1", "a.xml", ["ingestion"])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            report.save_json(path)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["execution_id"] == "exec-save-test"

    def test_save_json_creates_parent_dirs(self):
        report = RunReport()
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = Path(tmpdir) / "nested" / "dir" / "report.json"
            report.save_json(deep_path)
            assert deep_path.exists()

    def test_log_summary_does_not_raise(self):
        report = RunReport(execution_id="log-test")
        report.mark_processed("d1", "a.xml", ["ingestion"])
        report.mark_failed("d2", "b.xml", "temporal", "error")
        report.log_summary()  # should not raise

    def test_record_method_appends_status(self):
        report = RunReport()
        status = DocumentStatus(doc_id="x", filename="x.xml", status="processed")
        report.record(status)
        assert report.total_count == 1
        assert report.documents[0].doc_id == "x"


# ---------------------------------------------------------------------------
# PhaseSummary unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhaseSummary:
    def test_default_zero_counts(self):
        ps = PhaseSummary(phase="ingestion")
        assert ps.documents_attempted == 0
        assert ps.documents_succeeded == 0
        assert ps.documents_failed == 0

    def test_phase_summary_no_failures(self):
        report = RunReport()
        for i in range(5):
            report.mark_processed(f"d{i}", f"f{i}.xml", ["ingestion"])
        summary = report.phase_summary()
        assert summary["ingestion"].documents_succeeded == 5
        assert summary["ingestion"].documents_failed == 0
