"""Integration tests for nominal coverage probe metrics on live graph data."""

from __future__ import annotations

import pytest


def _neo4j_available() -> bool:
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


def _refinement_deps_available() -> bool:
    try:
        import spacy  # noqa: F401
        from textgraphx.RefinementPhase import RefinementPhase  # noqa: F401

        return True
    except Exception:
        return False


neo4j_required = pytest.mark.skipif(
    not _neo4j_available(),
    reason="Neo4j unavailable; skipping nominal probe integration tests",
)

refinement_deps = pytest.mark.skipif(
    not _refinement_deps_available(),
    reason="Refinement dependencies unavailable; skipping nominal probe integration tests",
)


@pytest.fixture
def graph():
    from textgraphx.neo4j_client import make_graph_from_config

    g = make_graph_from_config()
    try:
        yield g
    finally:
        if hasattr(g, "close"):
            g.close()


@neo4j_required
@refinement_deps
@pytest.mark.integration
@pytest.mark.slow
def test_numeric_value_refinement_subtype_metrics_non_regressive(graph):
    """numeric_value refinement should not regress quantified subtype coverage."""
    from textgraphx.tools.nominal_coverage_probe import _compute_delta, _run_refinement, _snapshot

    before = _snapshot(graph, doc_id=None)

    # Execute the same family used in runtime probes.
    _run_refinement("numeric_value")

    after = _snapshot(graph, doc_id=None)
    delta = _compute_delta(before, after)

    assert "nominal_entities_by_subtype" in before
    assert "nominal_entities_by_subtype" in after
    assert "quantified_nominal_entities_by_subtype" in before
    assert "quantified_nominal_entities_by_subtype" in after

    # Running refinement repeatedly should be idempotent or additive, not destructive.
    assert delta["entities_nominal"] >= 0
    assert delta["nominal_mentions_label"] >= 0

    before_q = before["quantified_nominal_entities_by_subtype"]
    after_q = after["quantified_nominal_entities_by_subtype"]
    for subtype in ("QUANTIFIED", "PARTITIVE"):
        assert after_q.get(subtype, 0) >= before_q.get(subtype, 0)

    # Subtype totals must never exceed total nominal entities.
    assert sum(after["nominal_entities_by_subtype"].values()) <= after["entities_nominal"]
