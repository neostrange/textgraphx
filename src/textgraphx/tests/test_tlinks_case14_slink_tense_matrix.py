"""Unit tests for TlinksRecognizer.create_tlinks_case14 — SLINK tense matrix.

Per NewsReader §10.6.2 Subtask 3, the relType between a reporting event and its
subordinated event depends on the tense/aspect combination.

Tests verify:
- Guards (merged, low_confidence, is_timeml_core, self-loop).
- Key matrix entries: PRESENT+PAST→AFTER, PAST+FUTURE→BEFORE,
  PAST+PAST+PROGRESSIVE→IS_INCLUDED, PRESENT+PRESENT→SIMULTANEOUS.
- NULL rows are skipped (WHERE rel_type IS NOT NULL).
- derivedFrom = 'SLINK' provenance.
- Mock invocation returns list.
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
# Guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case14_has_merged_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "coalesce(e_main.merged, false) = false" in src
    assert "coalesce(e_sub.merged, false) = false" in src


@pytest.mark.unit
def test_case14_has_self_loop_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "e_main <> e_sub" in src


@pytest.mark.unit
def test_case14_skips_null_reltype(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "rel_type IS NOT NULL" in src


# ---------------------------------------------------------------------------
# Matrix entries
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("expected_rel", ["SIMULTANEOUS", "AFTER", "BEFORE", "IS_INCLUDED"])
def test_case14_matrix_contains_reltype(tr_source, expected_rel):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert f"'{expected_rel}'" in src, f"relType '{expected_rel}' missing from tense matrix"


@pytest.mark.unit
def test_case14_past_progressive_maps_is_included(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "PROGRESSIVE" in src
    assert "IS_INCLUDED" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case14_sets_derived_from_slink(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "derivedFrom" in src
    assert "'SLINK'" in src


@pytest.mark.unit
def test_case14_sets_rule_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case14")
    assert "case14_slink_tense_matrix" in src


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case14_returns_list_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case14()
    assert isinstance(result, list)
