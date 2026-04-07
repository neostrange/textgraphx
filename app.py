from __future__ import annotations

from pathlib import Path
from typing import Iterable
import time
import sys
import logging

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestration import PipelineOrchestrator, ExecutionHistory, JobScheduler
from logging_utils import get_logger, log_section

# Setup logging for the UI
logger = get_logger(__name__)
logger.info("Starting textgraphx Streamlit UI")


PHASE_OPTIONS = [
    ("ingestion", "Ingestion (GraphBasedNLP)"),
    ("refinement", "Refinement"),
    ("temporal", "Temporal"),
    ("event_enrichment", "Event Enrichment"),
    ("tlinks", "TLINKs"),
]


def save_uploaded_files(uploaded_files: Iterable, dataset_dir: str) -> int:
    dataset_path = Path(dataset_dir)
    dataset_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving uploaded files to {dataset_dir}")

    saved = 0
    for uploaded in uploaded_files:
        target = dataset_path / uploaded.name
        target.write_bytes(uploaded.getbuffer())
        saved += 1
        logger.debug(f"  Saved: {uploaded.name} ({uploaded.size} bytes)")
    
    logger.info(f"Successfully saved {saved} files")
    return saved


def main() -> None:
    st.set_page_config(page_title="textgraphx Pipeline UI", layout="wide")
    st.title("📊 textgraphx Pipeline Orchestrator")
    st.caption("Run, schedule, and monitor the textgraphx NLP pipeline.")

    logger.info("UI loaded - main() called")

    # Initialize history
    history = ExecutionHistory()

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Run Pipeline", "Execution History", "Scheduling"])

    default_dataset = str((Path(__file__).resolve().parent / "datastore" / "dataset").resolve())

    with tab1:
        st.header("Run Pipeline")
        
        with st.sidebar:
            st.header("Pipeline Configuration")
            dataset_dir = st.text_input("Input dataset directory", value=default_dataset)
            model_name = st.selectbox(
                "spaCy model",
                options=["en_core_web_sm", "en_core_web_trf", "sm", "trf"],
                index=0,
            )
            
            logger.debug(f"Configuration - dataset_dir: {dataset_dir}, model_name: {model_name}")

            st.subheader("Upload files to dataset")
            uploaded_files = st.file_uploader(
                "Upload document files",
                accept_multiple_files=True,
                type=["xml", "txt"],
                help="Uploaded files are saved directly into the selected dataset directory.",
            )

            if uploaded_files:
                logger.info(f"Files uploaded: {len(uploaded_files)} file(s)")
                count = save_uploaded_files(uploaded_files, dataset_dir)
                st.success(f"Saved {count} file(s) to {dataset_dir}")

        st.subheader("Select phases to run")
        selected = {}
        for phase_key, label in PHASE_OPTIONS:
            selected[phase_key] = st.checkbox(label, value=True)

        selected_phases = [phase for phase, enabled in selected.items() if enabled]
        logger.info(f"Selected phases: {selected_phases}")

        run_clicked = st.button("Run Pipeline", type="primary")

        if run_clicked:
            if not selected_phases:
                st.warning("Please select at least one phase.")
                logger.warning("Pipeline run clicked but no phases selected")
                return

            logger.info(f"Running pipeline with phases: {selected_phases}")
            
            phase_map = {
                "ingestion": "Ingestion",
                "refinement": "Refinement",
                "temporal": "Temporal",
                "event_enrichment": "Event Enrichment",
                "tlinks": "TLINKs",
            }

            orchestrator = PipelineOrchestrator(directory=dataset_dir, model_name=model_name)

            # Create progress tracker
            progress_bar = st.progress(0)
            status_text = st.empty()
            phase_details = st.empty()

            with st.status("Running pipeline...", expanded=True) as status:
                try:
                    logger.info(f"Starting pipeline execution with {len(selected_phases)} phases")
                    
                    # Run all selected phases
                    orchestrator.run_selected(selected_phases)

                    logger.info("Pipeline execution completed successfully")
                    
                    # Update progress
                    progress_bar.progress(100)
                    status_text.success("✅ All phases completed successfully!")

                    # Display results summary
                    st.divider()
                    st.subheader("📊 Execution Summary")

                    summary = orchestrator.summary

                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Duration", f"{summary.total_duration:.1f}s")
                    with col2:
                        st.metric("Phases Completed", f"{summary.success_count}/{summary.phase_count}")
                    with col3:
                        st.metric("Documents Processed", summary.total_documents or "N/A")
                    with col4:
                        st.metric("Status", "✅ Success" if summary.failed_count == 0 else "❌ Failed")
                    
                    logger.info(f"Pipeline summary: total_duration={summary.total_duration:.2f}s, "
                               f"success_count={summary.success_count}, failed_count={summary.failed_count}")

                    # Detailed phase breakdown
                    st.subheader("Phase Timings")
                    phase_data = []
                    for phase_name in ["ingestion", "refinement", "temporal", "event_enrichment", "tlinks"]:
                        if phase_name in summary.phases:
                            phase = summary.phases[phase_name]
                            status_icon = "✅" if phase.status == "completed" else "❌" if phase.status == "failed" else "⏳"
                            phase_data.append({
                                "Phase": f"{status_icon} {phase_name.replace('_', ' ').title()}",
                                "Duration": f"{phase.duration:.2f}s",
                                "Status": phase.status.title()
                            })

                    if phase_data:
                        # Display without triggering pandas import
                        for phase_info in phase_data:
                            st.text(f"{phase_info['Phase']} - {phase_info['Duration']} - {phase_info['Status']}")

                    status.update(label="Pipeline completed successfully ✅", state="complete")

                except Exception as exc:
                    progress_bar.progress(100)
                    status_text.error(f"❌ Pipeline failed: {exc}")
                    status.update(label="Pipeline failed ❌", state="error")

                    # Show partial results if any phases completed
                    if orchestrator.summary.success_count > 0:
                        st.info("Partial results from completed phases:")
                        st.write(f"  Phases completed: {orchestrator.summary.success_count}")

                    st.exception(exc)

    # ===== EXECUTION HISTORY TAB =====
    with tab2:
        st.header("Execution History")

        # Statistics
        stats = history.get_statistics()
        if stats:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Runs", stats.total_runs)
            with col2:
                st.metric("Successful", stats.successful_runs)
            with col3:
                st.metric("Failed", stats.failed_runs)
            with col4:
                success_rate = (
                    f"{(stats.successful_runs/stats.total_runs*100):.1f}%"
                    if stats.total_runs > 0 else "N/A"
                )
                st.metric("Success Rate", success_rate)
            with col5:
                st.metric("Avg Duration", f"{stats.avg_duration:.1f}s" if stats.avg_duration else "N/A")

        st.divider()

        # Recent executions
        st.subheader("Recent Executions")
        records = history.get_latest(limit=20)

        if records:
            for record in records:
                status_icon = "✅" if record.status == "success" else "❌"
                st.text(f"{status_icon} {record.execution_id[:8]} - {record.status} ({record.total_duration:.1f}s) | {record.started_at[:10]}")
        else:
            st.info("No execution history available yet.")

    # ===== SCHEDULING TAB =====
    with tab3:
        st.header("Schedule Pipeline Runs")

        scheduler = JobScheduler()

        # Current jobs
        st.subheader("Scheduled Jobs")
        jobs = scheduler.list_jobs()

        if jobs:
            for job_id, job_info in jobs.items():
                schedule_str = job_info.get("cron_expression", f"Every {job_info.get('hours', 24)}h")
                st.text(f"{job_id[:8]} ({job_info['type']}) - {schedule_str}")
        else:
            st.info("No scheduled jobs yet.")

        st.divider()

        # Create new schedule
        st.subheader("Create New Schedule")

        col1, col2 = st.columns(2)

        with col1:
            schedule_type = st.radio("Schedule Type", ["Interval", "Cron"])
            job_id = st.text_input("Job ID (unique name)", value="job-1")
            dataset_path = st.text_input("Dataset Path", value=default_dataset)

        with col2:
            phases_for_schedule = st.multiselect(
                "Phases to run",
                options=[p[0] for p in PHASE_OPTIONS],
                default=["ingestion", "refinement"],
            )

            if schedule_type == "Interval":
                hours = st.number_input("Run every N hours", min_value=1, max_value=168, value=24)
                cron_expr = None
            else:
                cron_expr = st.text_input(
                    "Cron expression (minute hour day month weekday)",
                    value="0 2 * * *",
                    help="Example: '0 2 * * *' = Daily at 2 AM",
                )
                hours = None

        if st.button("Schedule Job", type="primary"):
            try:
                if schedule_type == "Interval":
                    success = scheduler.schedule_interval(
                        job_id=job_id,
                        dataset_path=dataset_path,
                        phases=phases_for_schedule,
                        hours=hours,
                    )
                else:
                    success = scheduler.schedule_cron(
                        job_id=job_id,
                        dataset_path=dataset_path,
                        phases=phases_for_schedule,
                        cron_expression=cron_expr,
                    )

                if success:
                    st.success(f"✅ Scheduled job: {job_id}")
                    st.rerun()
                else:
                    st.error("Failed to schedule job. Check logs.")
            except Exception as e:
                st.error(f"Error scheduling job: {e}")


if __name__ == "__main__":
    main()
