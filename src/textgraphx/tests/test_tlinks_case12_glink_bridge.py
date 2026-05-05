"""Unit tests for TlinksRecognizer.create_tlinks_case12 — GLINK→TLINK bridge.

Tests verify:
- Source code carries required guards (merged, low_confidence, is_timeml_core).
- Lemma → relType mapping is correct and BEGUN_BY / ENDED_BY / INCLUDES /
  SIMULTANEOUS are all represented.
- A mock invocation returns list output (never raises).
- NULL branch (unmapped lemma) is not inserted (WHERE rel_type IS NOT NULL).
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

TR_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "tlinks_recognizer.py"
)


@pytest.fixture(scope="module")
def tr_source() -> str:
    return TR_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


def _make_recognizer():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"created": 0}]
    return obj


# ---------------------------------------------------------------------------
# Source-level guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case12_has_merged_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "coalesce(e_src.merged, false) = false" in src
    assert "coalesce(e_tgt.merged, false) = false" in src


@pytest.mark.unit
def test_case12_has_low_confidence_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "coalesce(e_src.low_confidence, false) = false" in src
    assert "coalesce(e_tgt.low_confidence, false) = false" in src


@pytest.mark.unit
def test_case12_has_is_timeml_core_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "coalesce(e_src.is_timeml_core, true) = true" in src


# ---------------------------------------------------------------------------
# Reltype mapping completeness
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case12_maps_begun_by(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "'BEGUN_BY'" in src


@pytest.mark.unit
def test_case12_maps_ended_by(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "'ENDED_BY'" in src


@pytest.mark.unit
def test_case12_maps_includes(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "'INCLUDES'" in src


@pytest.mark.unit
def test_case12_maps_simultaneous(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "'SIMULTANEOUS'" in src


@pytest.mark.unit
def test_case12_skips_null_rel(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "inferred_rel IS NOT NULL" in src


# ---------------------------------------------------------------------------
# Provenance properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case12_sets_rule_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "case12_glink_bridge" in src


@pytest.mark.unit
def test_case12_sets_source_t2g(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "tl.source           = 't2g'" in src or "tl.source = 't2g'" in src


@pytest.mark.unit
def test_case12_uses_merge(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case12")
    assert "MERGE" in src


# ---------------------------------------------------------------------------
# Mock invocation — must not raise
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case12_returns_list_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case12()
    assert isinstance(result, list)
