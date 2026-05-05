"""Unit tests for TlinksRecognizer.create_tlinks_case16 — cross-sentence main events.

NewsReader Subtask 2: link the primary verbal event of each sentence to the
primary verbal event of the adjacent sentence, forming the narrative backbone.

Tests verify:
- Sentence index parsing via split(s1.id, '_').
- Consecutive sentence constraint (sn1 + 1).
- Finite tense filter: PAST / PRESENT / FUTURE.
- Verbal POS filter: VBZ, VBP, VBD, VBN, VB, MD.
- collect()[0] idiom for earliest event selection.
- Self-loop guard (e1_main <> e2_main).
- Tense-based relType CASE expression present.
- Confidence 0.65.
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
# Sentence ordering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case16_uses_split_sentence_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "split(s1.id, '_')" in src or "split(s2.id, '_')" in src


@pytest.mark.unit
def test_case16_has_consecutive_sentence_filter(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "sn1 + 1" in src


# ---------------------------------------------------------------------------
# Event selection filters
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("tense", ["'PAST'", "'PRESENT'", "'FUTURE'"])
def test_case16_includes_tense(tr_source, tense):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert tense in src, f"tense {tense} missing from Case 16"


@pytest.mark.unit
@pytest.mark.parametrize("pos", ["'VBD'", "'VBP'", "'VBZ'", "'MD'"])
def test_case16_includes_pos(tr_source, pos):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert pos in src, f"POS {pos} missing from Case 16"


@pytest.mark.unit
def test_case16_uses_first_event_idiom(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    # collect()[0] picks the earliest event
    assert "collect(" in src


@pytest.mark.unit
def test_case16_has_self_loop_guard(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "e1_main <> e2_main" in src or "e1 <> e2" in src


# ---------------------------------------------------------------------------
# RelType CASE expression
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case16_has_tense_reltype_case(tr_source):
    """Case 16 tense-based rules were evaluated and produced 0 TPs / several FPs.
    All rules except the SIMULTANEOUS stub are disabled via WHEN false THEN ...
    The CASE expression must still be present (documents future re-evaluation)."""
    src = _extract_method(tr_source, "create_tlinks_case16")
    # SIMULTANEOUS stub remains as a placeholder for future re-evaluation
    assert "'SIMULTANEOUS'" in src
    # BEFORE tense rules are disabled (produced only FPs vs MEANTIME gold)
    # They must NOT appear as live relType assignments
    assert "WHEN false" in src or "false THEN" in src, (
        "Case 16 tense rules should be disabled via WHEN false; found active BEFORE rule"
    )


@pytest.mark.unit
def test_case16_skips_null_reltype(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "rel_type IS NOT NULL" in src


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case16_sets_rule_id(tr_source):
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "case16_cross_sentence_main_events" in src


@pytest.mark.unit
def test_case16_confidence_is_low(tr_source):
    """Cross-sentence inference must carry lower confidence (0.65)."""
    src = _extract_method(tr_source, "create_tlinks_case16")
    assert "0.65" in src


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case16_returns_list_from_mock():
    obj = _make_recognizer()
    result = obj.create_tlinks_case16()
    assert isinstance(result, list)
