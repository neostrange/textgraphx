"""
Execution history storage and retrieval for TextGraphX pipeline.
Stores pipeline executions to SQLite database for auditing and analysis.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from textgraphx.reasoning.temporal.time import utc_iso_now

logger = logging.getLogger(__name__)


class ExecutionRecord:
    """A single pipeline execution record."""

    def __init__(
        self,
        execution_id: str,
        dataset_path: str,
        phases: str,
        status: str,
        total_duration: float,
        phase_timings: Dict[str, float],
        documents_processed: int,
        error_message: Optional[str] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ):
        self.execution_id = execution_id
        self.dataset_path = dataset_path
        self.phases = phases
        self.status = status
        self.total_duration = total_duration
        self.phase_timings = phase_timings
        self.documents_processed = documents_processed
        self.error_message = error_message
        self.started_at = started_at or utc_iso_now()
        self.completed_at = completed_at or utc_iso_now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "execution_id": self.execution_id,
            "dataset_path": self.dataset_path,
            "phases": self.phases,
            "status": self.status,
            "total_duration": self.total_duration,
            "phase_timings": self.phase_timings,
            "documents_processed": self.documents_processed,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class ExecutionHistory:
    """Manages execution history storage and retrieval."""

    def __init__(self, db_path: str = ".textgraphx/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    dataset_path TEXT NOT NULL,
                    phases TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_duration REAL NOT NULL,
                    phase_timings TEXT NOT NULL,
                    documents_processed INTEGER DEFAULT 0,
                    error_message TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def store_execution(self, record: ExecutionRecord) -> bool:
        """Store an execution record to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO executions (
                        execution_id, dataset_path, phases, status,
                        total_duration, phase_timings, documents_processed,
                        error_message, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.execution_id,
                        record.dataset_path,
                        record.phases,
                        record.status,
                        record.total_duration,
                        json.dumps(record.phase_timings),
                        record.documents_processed,
                        record.error_message,
                        record.started_at,
                        record.completed_at,
                    ),
                )
                conn.commit()
            logger.info("Stored execution record: %s", record.execution_id)
            return True
        except Exception as e:
            logger.error("Failed to store execution: %s", e)
            return False

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Retrieve a specific execution record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM executions WHERE execution_id = ?",
                    (execution_id,),
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_record(row)
        except Exception as e:
            logger.error("Failed to retrieve execution: %s", e)
        return None

    def get_latest(self, limit: int = 10) -> List[ExecutionRecord]:
        """Retrieve latest execution records."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM executions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                return [self._row_to_record(row) for row in rows]
        except Exception as e:
            logger.error("Failed to retrieve history: %s", e)
        return []

    def get_by_dataset(self, dataset_path: str, limit: int = 50) -> List[ExecutionRecord]:
        """Retrieve execution records for a specific dataset."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM executions WHERE dataset_path = ? ORDER BY created_at DESC LIMIT ?",
                    (dataset_path, limit),
                )
                rows = cursor.fetchall()
                return [self._row_to_record(row) for row in rows]
        except Exception as e:
            logger.error("Failed to retrieve dataset history: %s", e)
        return []

    def get_statistics(self) -> Dict:
        """Get execution statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_runs,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                        AVG(total_duration) as avg_duration,
                        MAX(total_duration) as max_duration,
                        MIN(total_duration) as min_duration,
                        SUM(documents_processed) as total_documents
                    FROM executions
                    """
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "total_runs": row[0] or 0,
                        "successful_runs": row[1] or 0,
                        "failed_runs": row[2] or 0,
                        "avg_duration": row[3] or 0,
                        "max_duration": row[4] or 0,
                        "min_duration": row[5] or 0,
                        "total_documents": row[6] or 0,
                    }
        except Exception as e:
            logger.error("Failed to retrieve statistics: %s", e)
        return {}

    def delete_old_records(self, days: int = 30) -> int:
        """Delete execution records older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM executions
                    WHERE created_at < datetime('now', '-' || ? || ' days')
                    """,
                    (days,),
                )
                conn.commit()
                deleted = cursor.rowcount
                logger.info("Deleted %s old execution records", deleted)
                return deleted
        except Exception as e:
            logger.error("Failed to delete old records: %s", e)
        return 0

    @staticmethod
    def _row_to_record(row) -> ExecutionRecord:
        """Convert database row to ExecutionRecord."""
        if isinstance(row, sqlite3.Row):
            phase_timings = json.loads(row["phase_timings"])
        else:
            phase_timings = json.loads(row[5])

        return ExecutionRecord(
            execution_id=row[0] if isinstance(row, tuple) else row["execution_id"],
            dataset_path=row[1] if isinstance(row, tuple) else row["dataset_path"],
            phases=row[2] if isinstance(row, tuple) else row["phases"],
            status=row[3] if isinstance(row, tuple) else row["status"],
            total_duration=row[4] if isinstance(row, tuple) else row["total_duration"],
            phase_timings=phase_timings,
            documents_processed=row[6] if isinstance(row, tuple) else row["documents_processed"],
            error_message=row[7] if isinstance(row, tuple) else row["error_message"],
            started_at=row[8] if isinstance(row, tuple) else row["started_at"],
            completed_at=row[9] if isinstance(row, tuple) else row["completed_at"],
        )