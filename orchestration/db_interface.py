"""Database interface module for execution history management."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum


class ExecutionStatus(str, Enum):
    """Status of pipeline execution."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"


@dataclass
class ExecutionRecord:
    """Record of a pipeline execution."""
    execution_id: str
    status: str
    total_duration: float
    documents_processed: int
    phases: str  # comma-separated phase names
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ExecutionStatistics:
    """Statistics about pipeline executions."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration: float


class ExecutionHistory:
    """Manages pipeline execution history using JSON file storage."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the execution history storage.
        
        Args:
            db_path: Path to JSON file for storing history. Defaults to .textgraphx_history.json in home directory.
        """
        if db_path is None:
            db_path = str(Path.home() / ".textgraphx_history.json")
        
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database file if it doesn't exist."""
        if not self.db_path.exists():
            self.db_path.write_text(json.dumps({"executions": []}))

    def _load_data(self) -> Dict[str, Any]:
        """Load all data from the JSON file."""
        try:
            return json.loads(self.db_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"executions": []}

    def _save_data(self, data: Dict[str, Any]) -> None:
        """Save all data to the JSON file."""
        self.db_path.write_text(json.dumps(data, indent=2))

    def record_execution(
        self,
        execution_id: str,
        status: str,
        total_duration: float,
        documents_processed: int,
        phases: List[str],
        started_at: str,
        completed_at: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a pipeline execution.
        
        Args:
            execution_id: Unique identifier for the execution.
            status: Execution status (success, failed, etc).
            total_duration: Total execution time in seconds.
            documents_processed: Number of documents processed.
            phases: List of phases that were executed.
            started_at: ISO format datetime when execution started.
            completed_at: ISO format datetime when execution completed.
            error_message: Error message if execution failed.
        """
        phases_str = ",".join(phases)
        
        data = self._load_data()
        record = {
            "execution_id": execution_id,
            "status": status,
            "total_duration": total_duration,
            "documents_processed": documents_processed,
            "phases": phases_str,
            "started_at": started_at,
            "completed_at": completed_at,
            "error_message": error_message,
        }
        data["executions"].append(record)
        self._save_data(data)

    def get_latest(self, limit: int = 20) -> List[ExecutionRecord]:
        """Get the latest execution records.
        
        Args:
            limit: Maximum number of records to return.
            
        Returns:
            List of ExecutionRecord objects, sorted by started_at descending.
        """
        data = self._load_data()
        executions = data.get("executions", [])
        
        # Sort by started_at descending
        sorted_executions = sorted(executions, key=lambda x: x["started_at"], reverse=True)[:limit]
        
        records = []
        for exec_data in sorted_executions:
            records.append(ExecutionRecord(
                execution_id=exec_data["execution_id"],
                status=exec_data["status"],
                total_duration=exec_data["total_duration"],
                documents_processed=exec_data["documents_processed"],
                phases=exec_data["phases"],
                started_at=exec_data["started_at"],
                completed_at=exec_data.get("completed_at"),
                error_message=exec_data.get("error_message"),
            ))
        return records

    def get_statistics(self) -> Optional[ExecutionStatistics]:
        """Get execution statistics.
        
        Returns:
            ExecutionStatistics object with aggregated metrics, or None if no executions.
        """
        data = self._load_data()
        executions = data.get("executions", [])
        
        if not executions:
            return None
        
        total_runs = len(executions)
        successful_runs = sum(1 for e in executions if e["status"] == "success")
        failed_runs = sum(1 for e in executions if e["status"] == "failed")
        avg_duration = sum(e["total_duration"] for e in executions) / total_runs if total_runs > 0 else 0
        
        return ExecutionStatistics(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            avg_duration=avg_duration,
        )

    def get_by_status(self, status: str, limit: int = 50) -> List[ExecutionRecord]:
        """Get executions by status.
        
        Args:
            status: Status to filter by (e.g., 'success', 'failed').
            limit: Maximum number of records to return.
            
        Returns:
            List of ExecutionRecord objects.
        """
        data = self._load_data()
        executions = data.get("executions", [])
        
        filtered = [e for e in executions if e["status"] == status]
        sorted_executions = sorted(filtered, key=lambda x: x["started_at"], reverse=True)[:limit]
        
        records = []
        for exec_data in sorted_executions:
            records.append(ExecutionRecord(
                execution_id=exec_data["execution_id"],
                status=exec_data["status"],
                total_duration=exec_data["total_duration"],
                documents_processed=exec_data["documents_processed"],
                phases=exec_data["phases"],
                started_at=exec_data["started_at"],
                completed_at=exec_data.get("completed_at"),
                error_message=exec_data.get("error_message"),
            ))
        return records

    def delete_old_records(self, days: int = 30) -> int:
        """Delete execution records older than specified days.
        
        Args:
            days: Number of days to retain.
            
        Returns:
            Number of records deleted.
        """
        from datetime import datetime, timedelta
        
        data = self._load_data()
        executions = data.get("executions", [])
        
        cutoff_date = datetime.now() - timedelta(days=days)
        initial_count = len(executions)
        
        # Keep only recent records
        data["executions"] = [
            e for e in executions
            if datetime.fromisoformat(e["started_at"]) > cutoff_date
        ]
        
        self._save_data(data)
        return initial_count - len(data["executions"])
