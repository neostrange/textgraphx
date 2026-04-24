"""
REST API for TextGraphX pipeline orchestration.
Provides HTTP endpoints for triggering runs, checking status, and retrieving results.
"""

import logging
import uuid
from pathlib import Path
from typing import List, Optional

try:
    from textgraphx.reasoning.temporal.time import utc_iso_now
except ImportError:  # pragma: no cover - support script-style execution
    from time_utils import utc_iso_now

try:
    from textgraphx.orchestration.runtime_history import ExecutionHistory, ExecutionRecord
    from textgraphx.orchestration.runtime_summary import ExecutionSummary
except ImportError:  # pragma: no cover - support script-style execution
    from execution_history import ExecutionHistory, ExecutionRecord
    from execution_summary import ExecutionSummary

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from textgraphx.evaluation.diagnostics import (
    get_registered_diagnostics,
    get_runtime_metrics,
    list_diagnostic_queries,
    run_registered_diagnostic,
)
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.orchestration.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

# Initialize API
app = FastAPI(
    title="TextGraphX Pipeline API",
    description="REST API for running and monitoring the TextGraphX pipeline",
    version="1.0.0",
)

# Global state (in production, use proper job queue like Celery)
_execution_history = ExecutionHistory()
_active_runs = {}


# Request/Response Models
class PipelineRunRequest(BaseModel):
    """Request to run the pipeline."""
    dataset_path: str
    phases: List[str] = ["ingestion", "refinement", "temporal", "event_enrichment", "tlinks"]
    model_name: str = "en_core_web_trf"


class ExecutionStatus(BaseModel):
    """Status of a pipeline execution."""
    execution_id: str
    status: str  # queued, running, completed, failed
    dataset_path: str
    phases: List[str]
    total_duration: Optional[float] = None
    documents_processed: int = 0
    error_message: Optional[str] = None


class HistoryRecord(BaseModel):
    """A pipeline execution from history."""
    execution_id: str
    dataset_path: str
    phases: str
    status: str
    total_duration: float
    documents_processed: int
    started_at: str
    completed_at: str


class Statistics(BaseModel):
    """Pipeline execution statistics."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration: float
    max_duration: float
    min_duration: float
    total_documents: int


# API Endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Check API health and database connectivity."""
    try:
        stats = _execution_history.get_statistics()
        return {
            "status": "healthy",
            "timestamp": utc_iso_now(),
            "database": "connected" if stats else "unknown",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")


@app.post("/runs", tags=["Execution"], response_model=ExecutionStatus)
async def submit_run(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Submit a new pipeline run."""
    execution_id = str(uuid.uuid4())[:8]

    try:
        # Validate dataset path
        dataset_path = Path(request.dataset_path)
        if not dataset_path.exists():
            raise HTTPException(status_code=400, detail=f"Dataset path not found: {request.dataset_path}")

        # Queue execution
        _active_runs[execution_id] = {
            "status": "queued",
            "phases": request.phases,
            "dataset_path": request.dataset_path,
            "model_name": request.model_name,
        }

        # Run in background
        background_tasks.add_task(
            _run_pipeline,
            execution_id,
            request.dataset_path,
            request.phases,
            request.model_name,
        )

        logger.info(f"Submitted pipeline run: {execution_id}")

        return ExecutionStatus(
            execution_id=execution_id,
            status="queued",
            dataset_path=request.dataset_path,
            phases=request.phases,
        )

    except Exception as e:
        logger.error(f"Failed to submit run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{execution_id}", tags=["Execution"], response_model=ExecutionStatus)
async def get_run_status(execution_id: str):
    """Get status of a pipeline execution."""
    # Check active runs
    if execution_id in _active_runs:
        run = _active_runs[execution_id]
        return ExecutionStatus(
            execution_id=execution_id,
            status=run["status"],
            dataset_path=run["dataset_path"],
            phases=run["phases"],
        )

    # Check history
    record = _execution_history.get_execution(execution_id)
    if record:
        return ExecutionStatus(
            execution_id=execution_id,
            status=record.status,
            dataset_path=record.dataset_path,
            phases=record.phases.split(","),
            total_duration=record.total_duration,
            documents_processed=record.documents_processed,
            error_message=record.error_message,
        )

    raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")


@app.get("/runs", tags=["Execution"])
async def list_runs(limit: int = 20, dataset_path: Optional[str] = None):
    """List recent pipeline executions."""
    if dataset_path:
        records = _execution_history.get_by_dataset(dataset_path, limit=limit)
    else:
        records = _execution_history.get_latest(limit=limit)

    return [
        HistoryRecord(
            execution_id=r.execution_id,
            dataset_path=r.dataset_path,
            phases=r.phases,
            status=r.status,
            total_duration=r.total_duration,
            documents_processed=r.documents_processed,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in records
    ]


@app.get("/statistics", tags=["Analytics"], response_model=Statistics)
async def get_statistics():
    """Get pipeline execution statistics."""
    stats = _execution_history.get_statistics()
    return Statistics(**stats)


@app.get("/diagnostics/runtime", tags=["Analytics"])
async def get_runtime_diagnostics(totals_only: bool = False):
    """Return runtime diagnostics aggregated from registered query pack entries."""
    graph = make_graph_from_config()
    close_fn = getattr(graph, "close", None)
    try:
        payload = get_runtime_metrics(graph)
        if totals_only and isinstance(payload, dict):
            return payload.get("totals", {})
        return payload
    except Exception as e:
        logger.error(f"Failed to compute runtime diagnostics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if callable(close_fn):
            close_fn()


@app.get("/diagnostics/queries", tags=["Analytics"])
async def list_runtime_diagnostic_queries():
    """List registered runtime diagnostics queries and their expected output fields."""
    return get_registered_diagnostics()


@app.get("/diagnostics/query/{query_name}", tags=["Analytics"])
async def get_runtime_diagnostic_query(query_name: str):
    """Run one registered runtime diagnostics query by stable name."""
    if query_name not in list_diagnostic_queries():
        raise HTTPException(status_code=404, detail=f"Unknown diagnostics query: {query_name}")

    graph = make_graph_from_config()
    close_fn = getattr(graph, "close", None)
    try:
        return {
            "query_name": query_name,
            "rows": run_registered_diagnostic(graph, query_name),
        }
    except KeyError as e:
        logger.error(f"Unknown diagnostics query requested: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute diagnostics query '{query_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if callable(close_fn):
            close_fn()


# Background task for pipeline execution
async def _run_pipeline(
    execution_id: str,
    dataset_path: str,
    phases: List[str],
    model_name: str,
) -> None:
    """Run pipeline in background."""
    logger.info(f"Starting pipeline execution: {execution_id}")

    try:
        # Mark as running
        if execution_id in _active_runs:
            _active_runs[execution_id]["status"] = "running"

        # Create orchestrator and run
        orchestrator = PipelineOrchestrator(directory=dataset_path, model_name=model_name)
        orchestrator.summary.start()
        orchestrator.run_selected(phases)
        orchestrator.summary.finish()

        # Store result
        record = ExecutionRecord(
            execution_id=execution_id,
            dataset_path=dataset_path,
            phases=",".join(phases),
            status="success" if orchestrator.summary.failed_count == 0 else "failed",
            total_duration=orchestrator.summary.total_duration,
            phase_timings={
                name: phase.duration
                for name, phase in orchestrator.summary.phases.items()
            },
            documents_processed=orchestrator.summary.total_documents,
            error_message=None if orchestrator.summary.failed_count == 0 else "; ".join(
                orchestrator.summary.errors
            ),
        )

        _execution_history.store_execution(record)

        # Update active status
        if execution_id in _active_runs:
            _active_runs[execution_id]["status"] = record.status
            _active_runs[execution_id]["total_duration"] = record.total_duration

        logger.info(f"Completed pipeline execution: {execution_id}")

    except Exception as e:
        logger.error(f"Pipeline execution failed: {execution_id} - {e}")

        record = ExecutionRecord(
            execution_id=execution_id,
            dataset_path=dataset_path,
            phases=",".join(phases),
            status="failed",
            total_duration=0,
            phase_timings={},
            documents_processed=0,
            error_message=str(e),
        )

        _execution_history.store_execution(record)

        if execution_id in _active_runs:
            _active_runs[execution_id]["status"] = "failed"
            _active_runs[execution_id]["error"] = str(e)


if __name__ == "__main__":
    import uvicorn

    # Run: uvicorn api:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
