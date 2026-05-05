"""Unit tests for TlinksRecognizer.create_tlinks_case18 — expanded signal lexicon.

Case 18 extends Cases 1-3 by:
  a. Traversing Signal nodes to find temporal conjunction tokens.
  b. Expanding fa.signal matching to include 'when', 'while', 'as', 'once',
     'since', 'until', 'upon', 'following', 'prior', 'meanwhile'.

Expected relType mapping:
  when/while/as/once/meanwhile → SIMULTANEOUS
  after/following              → AFTER
  before/prior                 → BEFORE
  since                        → BEGUN_BY
  until                        → ENDED_BY
  upon                         → IAFTER

Tests verify:
- Signal node path (TRIGGERS → Signal) in query.
- fa.signal property path in secondary sub-case.
- All expected signal words present.
- relType mapping for each signal group.
- self-loop guard (e1 <> e2).
- Mock invocation returns tuple.
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
# Signal traversal path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case18_traverses_signal_nodes(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "Signal" in src


@pytest.mark.unit
def test_case18_traverses_fa_signal_property(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "fa.signal" in src


# ---------------------------------------------------------------------------
# Signal lexicon coverage
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("signal_word", [
    "when", "while", "since", "until", "upon", "before", "after", "following"
])
def test_case18_includes_signal_word(tr_source, signal_word):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert f"'{signal_word}'" in src, f"signal word '{signal_word}' missing from Case 18"


# ---------------------------------------------------------------------------
# RelType mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case18_maps_simultaneous_for_when(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "'SIMULTANEOUS'" in src


@pytest.mark.unit
def test_case18_maps_begun_by_for_since(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "'BEGUN_BY'" in src


@pytest.mark.unit
def test_case18_maps_ended_by_for_until(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "'ENDED_BY'" in src


@pytest.mark.unit
def test_case18_maps_iafter_for_upon(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "'IAFTER'" in src


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case18_has_self_loop_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "e1 <> e2" in src


@pytest.mark.unit
def test_case18_skips_null_reltype(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "rel_type IS NOT NULL" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case18_sets_rule_ids(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case18")
    assert "case18_signal_node_expansion" in src
    assert "case18b_fa_signal_expansion" in src


# ---------------------------------------------------------------------------
# Mock — must return tuple (results, results_b)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case18_returns_tuple_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case18()
    assert isinstance(result, tuple), "create_tlinks_case18 must return (results, results_b)"
    assert len(result) == 2
    r1, r2 = result
    assert isinstance(r1, list)
    assert isinstance(r2, list)
