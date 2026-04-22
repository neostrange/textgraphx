"""Per-document run report for the textgraphx pipeline.

Tracks the outcome of each document through every phase so operators can
quickly see which files were processed, skipped, or failed and why.

Public surface
--------------
* ``DocumentStatus``  – dataclass for one document's outcome.
* ``RunReport``       – accumulates statuses, emits logs and JSON.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from textgraphx.time_utils import utc_iso_now

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DocumentStatus:
    """Outcome record for a single document in the pipeline."""

    doc_id: str
    filename: str
    status: str                          # "processed" | "skipped" | "failed"
    phases_completed: List[str] = field(default_factory=list)
    failed_phase: Optional[str] = None
    reason: Optional[str] = None
    duration_seconds: Optional[float] = None
    started_at: Optional[str] = None     # ISO timestamp


@dataclass
class PhaseSummary:
    """Aggregate counts for one phase in the run report."""

    phase: str
    documents_attempted: int = 0
    documents_succeeded: int = 0
    documents_failed: int = 0
    total_duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Report accumulator
# ---------------------------------------------------------------------------


class RunReport:
    """Accumulates per-document outcomes and produces structured reports.

    Usage::

        report = RunReport(execution_id="abc-123")
        report.record(DocumentStatus(doc_id="doc1", filename="a.xml",
                                     status="processed", phases_completed=["ingestion"]))
        report.log_summary()
        report.save_json(Path("run_report.json"))
    """

    def __init__(self, execution_id: str = "") -> None:
        self.execution_id = execution_id or utc_iso_now()
        self.created_at: str = utc_iso_now()
        self._documents: List[DocumentStatus] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, status: DocumentStatus) -> None:
        """Add a document outcome to the report."""
        self._documents.append(status)

    def mark_processed(
        self,
        doc_id: str,
        filename: str,
        phases_completed: List[str],
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Convenience method: record a successfully processed document."""
        self.record(
            DocumentStatus(
                doc_id=doc_id,
                filename=filename,
                status="processed",
                phases_completed=phases_completed,
                duration_seconds=duration_seconds,
                started_at=utc_iso_now(),
            )
        )

    def mark_skipped(
        self, doc_id: str, filename: str, reason: str
    ) -> None:
        """Convenience method: record a skipped document with a reason."""
        self.record(
            DocumentStatus(
                doc_id=doc_id,
                filename=filename,
                status="skipped",
                reason=reason,
                started_at=utc_iso_now(),
            )
        )

    def mark_failed(
        self,
        doc_id: str,
        filename: str,
        failed_phase: str,
        reason: str,
        phases_completed: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Convenience method: record a document that failed in a specific phase."""
        self.record(
            DocumentStatus(
                doc_id=doc_id,
                filename=filename,
                status="failed",
                phases_completed=phases_completed or [],
                failed_phase=failed_phase,
                reason=reason,
                duration_seconds=duration_seconds,
                started_at=utc_iso_now(),
            )
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def documents(self) -> List[DocumentStatus]:
        return list(self._documents)

    @property
    def processed_count(self) -> int:
        return sum(1 for d in self._documents if d.status == "processed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for d in self._documents if d.status == "skipped")

    @property
    def failed_count(self) -> int:
        return sum(1 for d in self._documents if d.status == "failed")

    @property
    def total_count(self) -> int:
        return len(self._documents)

    def failed_documents(self) -> List[DocumentStatus]:
        return [d for d in self._documents if d.status == "failed"]

    def phase_summary(self) -> Dict[str, PhaseSummary]:
        """Return per-phase aggregated counts across all documents."""
        summaries: Dict[str, PhaseSummary] = {}
        for doc in self._documents:
            for phase in doc.phases_completed:
                if phase not in summaries:
                    summaries[phase] = PhaseSummary(phase=phase)
                s = summaries[phase]
                s.documents_attempted += 1
                if doc.status == "failed" and doc.failed_phase == phase:
                    s.documents_failed += 1
                else:
                    s.documents_succeeded += 1
                if doc.duration_seconds:
                    s.total_duration_seconds += doc.duration_seconds
            # Also count attempted-but-failed phase
            if doc.failed_phase and doc.failed_phase not in doc.phases_completed:
                phase = doc.failed_phase
                if phase not in summaries:
                    summaries[phase] = PhaseSummary(phase=phase)
                summaries[phase].documents_attempted += 1
                summaries[phase].documents_failed += 1
        return summaries

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def log_summary(self) -> None:
        """Write a human-readable summary to the logger."""
        logger.info("=" * 60)
        logger.info("RUN REPORT  id=%s", self.execution_id)
        logger.info("=" * 60)
        logger.info(
            "Documents: %d total | %d processed | %d skipped | %d failed",
            self.total_count,
            self.processed_count,
            self.skipped_count,
            self.failed_count,
        )

        if self.failed_documents():
            logger.warning("Failed documents:")
            for doc in self.failed_documents():
                logger.warning(
                    "  ✗ %s  phase=%s  reason=%s",
                    doc.filename,
                    doc.failed_phase or "unknown",
                    doc.reason or "unknown",
                )

        phase_sums = self.phase_summary()
        if phase_sums:
            logger.info("Per-phase summary:")
            for ps in sorted(phase_sums.values(), key=lambda x: x.phase):
                logger.info(
                    "  %s: attempted=%d succeeded=%d failed=%d",
                    ps.phase,
                    ps.documents_attempted,
                    ps.documents_succeeded,
                    ps.documents_failed,
                )

        logger.info("=" * 60)

    def to_dict(self) -> Dict:
        """Serialize the entire report to a plain dictionary."""
        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at,
            "summary": {
                "total": self.total_count,
                "processed": self.processed_count,
                "skipped": self.skipped_count,
                "failed": self.failed_count,
            },
            "documents": [asdict(d) for d in self._documents],
            "phase_summary": {
                k: asdict(v) for k, v in self.phase_summary().items()
            },
        }

    def save_json(self, path: Path) -> None:
        """Write the report to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
        logger.info("Run report saved to %s", path)
