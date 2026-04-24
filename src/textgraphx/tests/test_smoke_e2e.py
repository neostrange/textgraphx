"""End-to-end smoke test for the textgraphx ingestion phase.

Runs a real ingestion on a single document and verifies that the expected
graph nodes (AnnotatedText, Sentence, TagOccurrence) are created in Neo4j.

Skip automatically when Neo4j is not running.
"""

import time
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neo4j_available() -> bool:
    """Return True only if a Neo4j connection can be established."""
    try:
        from textgraphx.health_check import check_neo4j_connection
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


def _count_nodes(session, label: str) -> int:
    result = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c")
    return result.single()["c"]


# ---------------------------------------------------------------------------
# Fixtures / markers
# ---------------------------------------------------------------------------

neo4j_required = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j is not running — skipping smoke test",
)

DATASET_DIR = str(
    Path(__file__).parent.parent / "datastore" / "dataset"
)
SMOKE_DOCUMENT = (
    Path(DATASET_DIR)
    / "$20m-AI-research-centre-set-up-in-South-Australia.naf.xml"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@neo4j_required
@pytest.mark.slow
def test_ingestion_creates_graph_nodes():
    """Ingestion phase should create AnnotatedText, Sentence and TagOccurrence nodes."""
    pytest.importorskip("textgraphx.orchestration")
    
    # Skip if spaCy C extensions are not available
    try:
        import spacy
    except ModuleNotFoundError as e:
        if "_ctypes" in str(e):
            pytest.skip("spaCy C extensions unavailable (_ctypes not found)")
        raise

    # Verify the test document is present
    if not SMOKE_DOCUMENT.exists():
        pytest.skip(f"Smoke-test document not found: {SMOKE_DOCUMENT}")

    from textgraphx.orchestration.orchestrator import PipelineOrchestrator
    from textgraphx.config import get_config
    from neo4j import GraphDatabase

    cfg = get_config()

    # Run ingestion
    start = time.time()
    orchestrator = PipelineOrchestrator(
        directory=DATASET_DIR,
        model_name="en_core_web_sm",
    )
    orchestrator.run_selected(["ingestion"])
    elapsed = time.time() - start

    assert elapsed < 300, f"Ingestion took too long: {elapsed:.1f}s (limit 300s)"

    # Verify Neo4j node counts
    driver = GraphDatabase.driver(
        cfg.neo4j.uri,
        auth=(cfg.neo4j.user, cfg.neo4j.password),
    )
    try:
        with driver.session() as session:
            annotated_text_count = _count_nodes(session, "AnnotatedText")
            sentence_count = _count_nodes(session, "Sentence")
            tag_occurrence_count = _count_nodes(session, "TagOccurrence")
    finally:
        driver.close()

    assert annotated_text_count >= 1, (
        f"Expected at least 1 AnnotatedText node, got {annotated_text_count}"
    )
    assert sentence_count >= 1, (
        f"Expected at least 1 Sentence node, got {sentence_count}"
    )
    assert tag_occurrence_count >= 10, (
        f"Expected at least 10 TagOccurrence nodes, got {tag_occurrence_count}"
    )
