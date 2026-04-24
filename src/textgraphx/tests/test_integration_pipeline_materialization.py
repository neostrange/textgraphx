"""Integration regression for strict materialization gate.

Ensures a real review run materializes temporal/event layers for the single-doc dataset.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _neo4j_available() -> bool:
    try:
        from textgraphx.infrastructure.health_check import check_neo4j_connection
        from textgraphx.config import get_config

        cfg = get_config()
        ok, _ = check_neo4j_connection(
            uri=cfg.neo4j.uri,
            user=cfg.neo4j.user,
            password=cfg.neo4j.password,
        )
        return ok
    except Exception:
        return False


def _pipeline_deps_available() -> bool:
    try:
        import spacy  # noqa: F401

        return True
    except Exception:
        return False


neo4j_required = pytest.mark.skipif(
    not _neo4j_available(), reason="Neo4j unavailable; skipping materialization integration test"
)

pipeline_deps = pytest.mark.skipif(
    not _pipeline_deps_available(), reason="spaCy/_ctypes unavailable for full pipeline integration"
)


@neo4j_required
@pipeline_deps
@pytest.mark.integration
@pytest.mark.slow
def test_review_run_materializes_temporal_event_layers():
    from textgraphx.orchestration.orchestrator import PipelineOrchestrator

    dataset_dir = str(Path(__file__).parent.parent / "datastore" / "dataset")
    orchestrator = PipelineOrchestrator(directory=dataset_dir, model_name="en_core_web_sm")

    prep = orchestrator.run_for_review()

    assert "already_processed" in prep
    gate = orchestrator.validate_materialization_gate()
    assert gate["passed"] is True
