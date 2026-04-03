from __future__ import annotations

from pathlib import Path
from typing import Iterable

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

        with st.status("Running pipeline...", expanded=True) as status:
            try:
                for phase in PipelineOrchestrator.PHASE_ORDER:
                    if phase not in selected_phases:
                        continue

                    status.write(f"Starting {phase_map[phase]}...")
                    with st.spinner(f"Executing {phase_map[phase]} phase"):
                        orchestrator.run_selected([phase])
                    status.write(f"Completed {phase_map[phase]}.")

                status.update(label="Pipeline completed successfully", state="complete")
                st.success("Pipeline run finished.")
            except Exception as exc:
                status.update(label="Pipeline failed", state="error")
                st.exception(exc)


if __name__ == "__main__":
    main()
