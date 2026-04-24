"""
Scheduling module for TextGraphX pipeline.
Allows scheduling recurring pipeline runs using APScheduler.
"""

import logging
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from textgraphx.reasoning.temporal.time import utc_iso_now, utc_timestamp_now

from .orchestrator import PipelineOrchestrator
from .runtime_history import ExecutionHistory, ExecutionRecord

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Manages scheduled pipeline executions."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.history = ExecutionHistory()
        self.jobs: Dict[str, Any] = {}

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("PipelineScheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("PipelineScheduler stopped")

    def schedule_interval(
        self,
        job_id: str,
        dataset_path: str,
        phases: list,
        hours: int = 24,
        model_name: str = "en_core_web_trf",
    ) -> bool:
        """Schedule a pipeline run at regular intervals."""
        try:
            trigger = IntervalTrigger(hours=hours)
            self.scheduler.add_job(
                self._run_and_store,
                trigger,
                id=job_id,
                args=(dataset_path, phases, model_name),
                replace_existing=True,
            )
            self.jobs[job_id] = {
                "type": "interval",
                "hours": hours,
                "dataset_path": dataset_path,
                "phases": phases,
                "created_at": utc_iso_now(),
            }
            logger.info("Scheduled interval job: %s (every %sh)", job_id, hours)
            return True
        except Exception as e:
            logger.error("Failed to schedule interval job: %s", e)
            return False

    def schedule_cron(
        self,
        job_id: str,
        dataset_path: str,
        phases: list,
        cron_expression: str,
        model_name: str = "en_core_web_trf",
    ) -> bool:
        """Schedule a pipeline run using cron expression."""
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 parts (minute hour day month weekday)")

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
            self.scheduler.add_job(
                self._run_and_store,
                trigger,
                id=job_id,
                args=(dataset_path, phases, model_name),
                replace_existing=True,
            )
            self.jobs[job_id] = {
                "type": "cron",
                "cron_expression": cron_expression,
                "dataset_path": dataset_path,
                "phases": phases,
                "created_at": utc_iso_now(),
            }
            logger.info("Scheduled cron job: %s (%s)", job_id, cron_expression)
            return True
        except Exception as e:
            logger.error("Failed to schedule cron job: %s", e)
            return False

    def unschedule(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info("Unscheduled job: %s", job_id)
            return True
        except Exception as e:
            logger.error("Failed to unschedule job: %s", e)
            return False

    def list_jobs(self) -> Dict[str, Any]:
        """List all scheduled jobs."""
        return self.jobs.copy()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific job."""
        return self.jobs.get(job_id)

    def _run_and_store(
        self,
        dataset_path: str,
        phases: list,
        model_name: str,
    ) -> None:
        """Run pipeline and store results. Called by scheduler."""
        execution_id = f"scheduled-{utc_timestamp_now()}".replace(".", "-")
        logger.info("Running scheduled pipeline: %s", execution_id)

        try:
            orchestrator = PipelineOrchestrator(directory=dataset_path, model_name=model_name)
            orchestrator.summary.start()
            orchestrator.run_selected(phases)
            orchestrator.summary.finish()

            record = ExecutionRecord(
                execution_id=execution_id,
                dataset_path=dataset_path,
                phases=",".join(phases),
                status="success" if orchestrator.summary.failed_count == 0 else "failed",
                total_duration=orchestrator.summary.total_duration,
                phase_timings={
                    name: phase.duration for name, phase in orchestrator.summary.phases.items()
                },
                documents_processed=orchestrator.summary.total_documents,
                error_message=None if orchestrator.summary.failed_count == 0 else "; ".join(
                    orchestrator.summary.errors
                ),
            )

            self.history.store_execution(record)
            logger.info("Completed scheduled pipeline: %s", execution_id)

        except Exception as e:
            logger.error("Scheduled pipeline failed: %s - %s", execution_id, e)

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

            self.history.store_execution(record)


_scheduler: Optional[PipelineScheduler] = None


def get_scheduler() -> PipelineScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
        _scheduler.start()
    return _scheduler