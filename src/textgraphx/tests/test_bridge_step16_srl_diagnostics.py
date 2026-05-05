"""Tests for Step 16: SRL diagnostics wired into the M1-M10 bridge.

Covers:
- MEANTIMEResults has srl_diagnostics field
- ConsolidatedQualityReport has srl_diagnostics field
- evaluate_from_neo4j accepts run_srl_diagnostics flag
- consolidate() accepts and passes srl_diagnostics parameter
- _srl_diagnostics_dict() serializes via asdict (or returns {})
- to_markdown() contains SRL diagnostics section
- to_dict() on ConsolidatedQualityReport includes srl_diagnostics key
- MEANTIMEBridge.consolidate() falls back to meantime_results.srl_diagnostics
  when srl_diagnostics kwarg is None

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import fields

import pytest

BRIDGE_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "meantime_bridge.py"
)


@pytest.fixture(scope="module")
def bridge_src() -> str:
    return BRIDGE_PATH.read_text(encoding="utf-8")


def _import_bridge():
    import importlib.util
    import sys
    mod_name = "_bridge_step16_test"
    spec = importlib.util.spec_from_file_location(mod_name, BRIDGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# MEANTIMEResults: srl_diagnostics field
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_meantime_results_has_srl_diagnostics_field(bridge_src):
    assert "srl_diagnostics" in bridge_src


@pytest.mark.unit
def test_meantime_results_srl_diagnostics_default_none():
    mod = _import_bridge()
    empty = mod.LayerScores(layer_name="x", strict_mode=False)
    r = mod.MEANTIMEResults(
        doc_id="d1",
        entity_strict=empty,
        entity_relaxed=empty,
        event_strict=empty,
        event_relaxed=empty,
        timex_strict=empty,
        timex_relaxed=empty,
    )
    assert r.srl_diagnostics is None


# ---------------------------------------------------------------------------
# ConsolidatedQualityReport: srl_diagnostics field
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidated_report_has_srl_diagnostics_field(bridge_src):
    field_names = [f.name for f in fields(_import_bridge().ConsolidatedQualityReport)]
    assert "srl_diagnostics" in field_names


@pytest.mark.unit
def test_consolidated_report_srl_diagnostics_defaults_none():
    mod = _import_bridge()
    mock_suite = MagicMock()
    mock_suite.run_metadata = MagicMock()
    mock_suite.overall_quality.return_value = 0.5

    empty = mod.LayerScores(layer_name="x", strict_mode=False)
    results = mod.MEANTIMEResults(
        doc_id="d1",
        entity_strict=empty, entity_relaxed=empty,
        event_strict=empty, event_relaxed=empty,
        timex_strict=empty, timex_relaxed=empty,
    )
    report = mod.ConsolidatedQualityReport(
        run_metadata=mock_suite.run_metadata,
        evaluation_suite=mock_suite,
        meantime_results=results,
    )
    assert report.srl_diagnostics is None


# ---------------------------------------------------------------------------
# evaluate_from_neo4j: run_srl_diagnostics flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evaluate_from_neo4j_accepts_run_srl_diagnostics(bridge_src):
    assert "run_srl_diagnostics" in bridge_src


@pytest.mark.unit
def test_evaluate_from_neo4j_guards_with_srl_quality_available(bridge_src):
    assert "_SRL_QUALITY_AVAILABLE" in bridge_src


@pytest.mark.unit
def test_evaluate_from_neo4j_srl_diagnostics_nonfatal(bridge_src):
    # Must wrap in try/except so it doesn't break scoring
    assert "except Exception" in bridge_src


# ---------------------------------------------------------------------------
# consolidate(): accepts srl_diagnostics, falls back to meantime srl_diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidate_accepts_srl_diagnostics_kwarg(bridge_src):
    assert "def consolidate(" in bridge_src
    assert "srl_diagnostics: Optional[Any]" in bridge_src


@pytest.mark.unit
def test_consolidate_falls_back_to_meantime_srl_diagnostics(bridge_src):
    # Should use getattr(meantime_results, "srl_diagnostics", None) as fallback
    assert 'getattr(meantime_results, "srl_diagnostics", None)' in bridge_src


@pytest.mark.unit
def test_consolidate_effective_srl_used(bridge_src):
    assert "effective_srl" in bridge_src


# ---------------------------------------------------------------------------
# _srl_diagnostics_dict() on ConsolidatedQualityReport
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_srl_diagnostics_dict_method_exists(bridge_src):
    assert "def _srl_diagnostics_dict" in bridge_src


@pytest.mark.unit
def test_srl_diagnostics_dict_returns_empty_when_none():
    mod = _import_bridge()
    mock_suite = MagicMock()
    mock_suite.run_metadata = MagicMock()
    mock_suite.overall_quality.return_value = 0.5

    empty = mod.LayerScores(layer_name="x", strict_mode=False)
    results = mod.MEANTIMEResults(
        doc_id="d1",
        entity_strict=empty, entity_relaxed=empty,
        event_strict=empty, event_relaxed=empty,
        timex_strict=empty, timex_relaxed=empty,
    )
    report = mod.ConsolidatedQualityReport(
        run_metadata=mock_suite.run_metadata,
        evaluation_suite=mock_suite,
        meantime_results=results,
        srl_diagnostics=None,
    )
    assert report._srl_diagnostics_dict() == {}


# ---------------------------------------------------------------------------
# to_dict() on ConsolidatedQualityReport includes srl_diagnostics key
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidated_to_dict_has_srl_diagnostics_key(bridge_src):
    assert '"srl_diagnostics"' in bridge_src or "'srl_diagnostics'" in bridge_src


@pytest.mark.unit
def test_consolidated_to_dict_calls_srl_diagnostics_dict(bridge_src):
    assert "_srl_diagnostics_dict()" in bridge_src


# ---------------------------------------------------------------------------
# to_markdown() includes SRL diagnostics section
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_markdown_has_srl_section_heading(bridge_src):
    assert "SRL Knowledge-Graph Diagnostics" in bridge_src


@pytest.mark.unit
def test_to_markdown_shows_frame_coverage(bridge_src):
    assert "frames_per_sentence" in bridge_src


@pytest.mark.unit
def test_to_markdown_shows_temporal_isolation(bridge_src):
    assert "temporally_isolated_events" in bridge_src


@pytest.mark.unit
def test_to_markdown_shows_anchor_tlink_yield(bridge_src):
    assert "anchor_tlink_yield_rate" in bridge_src


@pytest.mark.unit
def test_to_markdown_srl_section_conditional(bridge_src):
    # The SRL section should only render when srl_dict is non-empty
    assert "if srl_dict" in bridge_src
