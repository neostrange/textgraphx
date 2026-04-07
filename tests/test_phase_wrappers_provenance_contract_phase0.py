"""Regression tests locking wrapper provenance-contract wiring semantics."""

from pathlib import Path


def _phase_wrappers_source() -> str:
    return Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")


def test_temporal_wrapper_stamps_before_assertions_and_enforces_contracts():
    src = _phase_wrappers_source()

    stamp_idx = src.find('stamp_inferred_relationships(\n                        temporal.graph')
    assert_idx = src.find(').after_temporal()')
    enforce_idx = src.find('enforce_provenance_contracts=True')

    assert stamp_idx != -1
    assert assert_idx != -1
    assert enforce_idx != -1
    assert stamp_idx < assert_idx
    assert 'source_kind="service"' in src
    assert 'conflict_policy="merge"' in src


def test_event_wrapper_stamps_before_assertions_and_enforces_contracts():
    src = _phase_wrappers_source()

    stamp_idx = src.find('stamp_inferred_relationships(\n                        enricher.graph')
    assert_idx = src.find(').after_event_enrichment()')
    enforce_idx = src.find('enforce_provenance_contracts=True')

    assert stamp_idx != -1
    assert assert_idx != -1
    assert enforce_idx != -1
    assert stamp_idx < assert_idx
    assert 'source_kind="rule"' in src
    assert 'conflict_policy="additive"' in src


def test_tlinks_wrapper_stamps_before_assertions_and_enforces_contracts():
    src = _phase_wrappers_source()

    stamp_idx = src.find('stamp_inferred_relationships(\n                        recognizer.graph')
    assert_idx = src.find(').after_tlinks()')
    enforce_idx = src.find('enforce_provenance_contracts=True')

    assert stamp_idx != -1
    assert assert_idx != -1
    assert enforce_idx != -1
    assert stamp_idx < assert_idx
    assert 'source_kind="rule"' in src
    assert 'conflict_policy="additive"' in src
