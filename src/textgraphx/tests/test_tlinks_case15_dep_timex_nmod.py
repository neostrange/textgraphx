"""Unit tests for TlinksRecognizer.create_tlinks_case15 — dep-tree TIMEX→nominal event.

NewsReader Subtask 4: non-verbal event + TIMEX syntactic modifier.
e.g., "the 1992 crisis" → (crisis IS_INCLUDED 1992).

Tests verify:
- Dep relation set covers nmod, compound, tmod.
- Nominal POS filter (NN, NNS, NNP, NNPS).
- IS_INCLUDED relType.
- REFERS_TO traversal for TimexMention → canonical TIMEX.
- DISTINCT guard before MERGE.
- Mock invocation.
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
# Dep-parse relation set
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("dep_rel", ["nmod", "compound", "tmod"])
def test_case15_includes_dep_relation(tr_source, dep_rel):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert dep_rel in src, f"dep relation '{dep_rel}' missing from Case 15"


# ---------------------------------------------------------------------------
# Nominal POS filter
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("pos", ["'NN'", "'NNS'", "'NNP'", "'NNPS'"])
def test_case15_includes_pos(tr_source, pos):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert pos in src, f"POS {pos} missing from Case 15 nominal filter"


# ---------------------------------------------------------------------------
# RelType
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case15_assigns_is_included(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert "'IS_INCLUDED'" in src


# ---------------------------------------------------------------------------
# REFERS_TO traversal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case15_traverses_refers_to(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert "REFERS_TO" in src


@pytest.mark.unit
def test_case15_uses_distinct(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert "DISTINCT" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case15_sets_rule_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert "case15_dep_timex_nmod" in src


@pytest.mark.unit
def test_case15_uses_merge(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case15")
    assert "MERGE" in src


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case15_returns_list_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case15()
    assert isinstance(result, list)
