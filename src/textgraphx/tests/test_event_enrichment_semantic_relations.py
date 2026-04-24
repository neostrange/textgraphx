"""Source-contract tests for additional semantic relation types (M4.3)."""

from pathlib import Path

import pytest


def _event_enrichment_source() -> str:
    source_path = Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "event_enrichment.py"
    return source_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_add_semantic_relation_types_method_exists_in_source():
    src = _event_enrichment_source()
    assert "def add_semantic_relation_types" in src


@pytest.mark.unit
def test_semantic_relation_queries_include_modifies_and_affects():
    src = _event_enrichment_source()
    assert "MERGE (fa)-[r:MODIFIES]->(event)" in src
    assert "MERGE (src)-[r:AFFECTS]->(event)" in src


@pytest.mark.unit
def test_endpoint_contract_relations_include_modifies_and_affects():
    src = _event_enrichment_source()
    assert '"MODIFIES"' in src
    assert '"AFFECTS"' in src
