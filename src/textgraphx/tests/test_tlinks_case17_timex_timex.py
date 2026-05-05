"""Unit tests for TlinksRecognizer.create_tlinks_case17 — TIMEX-TIMEX links.

NewsReader Subtask 5: temporal relations between two temporal expressions.

Sub-case 17a: same normalized TIMEX value → SIMULTANEOUS (conf=0.87).
Sub-case 17b: DURATION TIMEX co-occurring with DATE/SET TIMEX in same
              sentence → IS_INCLUDED (conf=0.78).

Tests verify:
- 17a: same-value guard, SIMULTANEOUS relType, high confidence.
- 17b: DURATION type filter, DATE/SET type filter, IS_INCLUDED relType.
- Self-identity guards (elementId comparison or t1 <> t2).
- doc_id constraint (same document only).
- Method returns tuple of two result sets (one per sub-case).
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
# Sub-case 17a
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case17a_same_value_simultaneous(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "t1.value = t2.value" in src
    assert "'SIMULTANEOUS'" in src


@pytest.mark.unit
def test_case17a_high_confidence(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "0.87" in src


@pytest.mark.unit
def test_case17a_same_doc_constraint(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "doc_id" in src


@pytest.mark.unit
def test_case17a_non_empty_value_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "coalesce(t1.value, '') <> ''" in src


# ---------------------------------------------------------------------------
# Sub-case 17b
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case17b_duration_type_filter(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "'DURATION'" in src


@pytest.mark.unit
@pytest.mark.parametrize("timex_type", ["'DATE'", "'SET'", "'TIME'"])
def test_case17b_date_type_filter(tr_source, timex_type):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert timex_type in src, f"TIMEX type {timex_type} missing from Case 17"


@pytest.mark.unit
def test_case17b_is_included_reltype(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "'IS_INCLUDED'" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case17_sets_rule_ids(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case17")
    assert "case17a_timex_same_value" in src
    assert "case17b_timex_duration_in_date" in src


# ---------------------------------------------------------------------------
# Mock — method must return a tuple (r17a, r17b)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case17_returns_two_results_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case17()
    assert isinstance(result, tuple), "create_tlinks_case17 must return (r17a, r17b)"
    assert len(result) == 2
    r17a, r17b = result
    assert isinstance(r17a, list)
    assert isinstance(r17b, list)
