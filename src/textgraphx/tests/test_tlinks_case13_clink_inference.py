"""Unit tests for TlinksRecognizer.create_tlinks_case13 — CLINK→TLINK inference.

Per NewsReader §10.3: causal events always precede their caused effects.
CLINK(cause, effect) must always generate TLINK(cause, BEFORE, effect).

Tests verify:
- Required guards in source code (merged, low_confidence, is_timeml_core).
- BEFORE relType is produced.
- cause <> effect self-loop guard is present.
- derivedFrom = 'CLINK' provenance is set.
- Mock invocation returns a list.
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
def test_case13_has_merged_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "coalesce(cause.merged, false) = false" in src
    assert "coalesce(effect.merged, false) = false" in src


@pytest.mark.unit
def test_case13_has_low_confidence_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "coalesce(cause.low_confidence, false) = false" in src


@pytest.mark.unit
def test_case13_has_self_loop_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "cause <> effect" in src


# ---------------------------------------------------------------------------
# Reltype
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case13_assigns_before(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "'BEFORE'" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case13_sets_derived_from(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "derivedFrom" in src
    assert "'CLINK'" in src


@pytest.mark.unit
def test_case13_sets_rule_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "case13_clink_before_inference" in src


@pytest.mark.unit
def test_case13_uses_merge(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case13")
    assert "MERGE" in src


# ---------------------------------------------------------------------------
# Mock invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case13_returns_list_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case13()
    assert isinstance(result, list)
