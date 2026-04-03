from __future__ import annotations

from pathlib import Path
from typing import Iterable
import time

import streamlit as st

from PipelineOrchestrator import PipelineOrchestrator


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

    saved = 0
    for uploaded in uploaded_files:
        target = dataset_path / uploaded.name
        target.write_bytes(uploaded.getbuffer())
        saved += 1
    return saved


def main() -> None:
    st.set_page_config(page_title="textgraphx Pipeline UI", layout="wide")
    st.title("textgraphx Pipeline Orchestrator")
    st.caption("Run all pipeline phases or selected phases for iterative demos.")

    default_dataset = str((Path(__file__).resolve().parent / "datastore" / "dataset").resolve())

    with st.sidebar:
        st.header("Pipeline Configuration")
        dataset_dir = st.text_input("Input dataset directory", value=default_dataset)
        model_name = st.selectbox(
            "spaCy model",
            options=["en_core_web_sm", "en_core_web_trf", "sm", "trf"],
            index=0,
        )

        st.subheader("Upload files to dataset")
        uploaded_files = st.file_uploader(
            "Upload document files",
            accept_multiple_files=True,
            type=["xml", "txt"],
            help="Uploaded files are saved directly into the selected dataset directory.",
        )

        if uploaded_files:
            count = save_uploaded_files(uploaded_files, dataset_dir)
            st.success(f"Saved {count} file(s) to {dataset_dir}")

    st.subheader("Select phases to run")
    selected = {}
    for phase_key, label in PHASE_OPTIONS:
        selected[phase_key] = st.checkbox(label, value=True)

    selected_phases = [phase for phase, enabled in selected.items() if enabled]

    run_clicked = st.button("Run Pipeline", type="primary", use_container_width=True)

    if run_clicked:
        if not selected_phases:
            st.warning("Please select at least one phase.")
            return

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
                # Run all selected phases
                orchestrator.run_selected(selected_phases)

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
                    st.dataframe(phase_data, use_container_width=True)

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


if __name__ == "__main__":
    main()
