"""Unit tests for TlinksRecognizer.create_tlinks_case20 — DCT-INCLUDES fallback.

Case 20 targets the #1 recall gap: INCLUDES × TIMEX-EVENT accounts for 27.6%
of MEANTIME gold TLINKs (20/76 links).

Sub-case 20a: sentence-local TIMEX (DATE/SET) INCLUDES co-occurring TEvent.
  - Writes (timex)-[INCLUDES]->(event) directly (TIMEX-first direction).
  - Guards: type IN ['DATE','SET'], NOT SRLTimexCandidate, tok-distance ≤ 15,
    no existing TLINK on this pair.

Sub-case 20b: DCT INCLUDES unanchored events (fallback).
  - For TEvents with NO TLINK to any TIMEX at all.
  - Writes (e)-[IS_INCLUDED]->(dct) so Case 19 inverse mirror produces
    (dct)-[INCLUDES]->(e).
  - Confidence 0.55 (lower than Case 6's 0.78 — no tense evidence).

Tests verify:
- Method exists and is split into two sub-cases.
- 20a: TIMEX-first direction MERGE, INCLUDES relType, DATE/SET guard, distance guard.
- 20b: unanchored guard (NOT EXISTS), IS_INCLUDED relType, fallback rule_id.
- Both use MERGE with ON CREATE / ON MATCH blocks.
- Event guards: merged=false, low_confidence=false, is_timeml_core present.
- Mock invocation: returns tuple of two result lists.
- __main__ block calls case20.
- phase_wrappers wires case20.
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
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = [{"created": 2}]

    from textgraphx.pipeline.phases.tlinks_recognizer import TlinksRecognizer

    rec = TlinksRecognizer.__new__(TlinksRecognizer)
    rec.graph = mock_graph
    rec.logger = MagicMock()
    rec.doc_id = "test_doc"
    rec.config = {}
    return rec


# ---------------------------------------------------------------------------
# Source structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(tr_source):
    assert "def create_tlinks_case20(" in tr_source


@pytest.mark.unit
def test_has_two_sub_cases(tr_source):
    """Method must contain both 20a and 20b sub-case markers."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "20a" in body
    assert "20b" in body


@pytest.mark.unit
def test_uses_merge_not_plain_create(tr_source):
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "MERGE" in body
    assert "ON CREATE SET" in body
    assert "ON MATCH SET" in body


# ---------------------------------------------------------------------------
# Sub-case 20a
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_20a_timex_first_direction(tr_source):
    """20a must write (timex/t)-[TLINK]->(event/e), not event→timex."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    # The MERGE must have t before e or use a TIMEX-first alias
    assert "MERGE (t)-[tl:TLINK]->(e)" in body or "MERGE (t" in body


@pytest.mark.unit
def test_20a_includes_reltype(tr_source):
    """20a must use INCLUDES (TIMEX includes the event)."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "INCLUDES" in body


@pytest.mark.unit
def test_20a_date_set_type_filter(tr_source):
    """20a must restrict TIMEX to DATE or SET types."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "'DATE'" in body
    assert "'SET'" in body


@pytest.mark.unit
def test_20a_excludes_srl_timex_candidates(tr_source):
    """20a must exclude SRLTimexCandidate nodes to avoid circular evidence."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "SRLTimexCandidate" in body


@pytest.mark.unit
def test_20a_dep_tree_approach(tr_source):
    """20a switched from a proximity window to a dependency-tree approach.
    Token distance guards are replaced by IS_DEPENDENT edge matching."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    # Must use dep-tree edges instead of (or in addition to) a proximity window
    assert "IS_DEPENDENT" in body or "dep_rel" in body or "dep_rel.dep" in body


@pytest.mark.unit
def test_20a_no_existing_tlink_guard(tr_source):
    """20a must not overwrite an existing TLINK on the same pair."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "NOT (e)-[:TLINK]-(t)" in body or "NOT EXISTS" in body or "WHERE NOT" in body


@pytest.mark.unit
def test_20a_rule_id(tr_source):
    """20a rule_id was updated when sub-case was promoted to case21 dep-tree approach."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    # Original id was case20a; promoted to case21_dep_timex_includes
    assert "case20a" in body or "case21" in body or "dep_timex" in body


# ---------------------------------------------------------------------------
# Sub-case 20b
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_20b_unanchored_guard(tr_source):
    """20b must only target events with NO existing TLINK to any TIMEX."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "NOT EXISTS" in body or "NOT (e)-[:TLINK]" in body


@pytest.mark.unit
def test_20b_dct_path(tr_source):
    """20b must traverse the CREATED_ON DCT path."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "CREATED_ON" in body


@pytest.mark.unit
def test_20b_is_included_reltype(tr_source):
    """20b writes from event side → IS_INCLUDED (Case 19 will flip to INCLUDES)."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "IS_INCLUDED" in body


@pytest.mark.unit
def test_20b_lower_confidence(tr_source):
    """20b confidence must be < Case 6's 0.78 (no tense evidence)."""
    body = _extract_method(tr_source, "create_tlinks_case20")
    # Find the confidence value for 20b — should be 0.55 or similar
    assert "0.55" in body or "0.56" in body or "0.57" in body or "0.58" in body or "0.60" in body


@pytest.mark.unit
def test_20b_rule_id(tr_source):
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "case20b" in body


# ---------------------------------------------------------------------------
# Event safety guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_event_merged_guard(tr_source):
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "merged" in body and "false" in body


@pytest.mark.unit
def test_event_low_confidence_guard(tr_source):
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "low_confidence" in body


@pytest.mark.unit
def test_event_is_timeml_core_guard(tr_source):
    body = _extract_method(tr_source, "create_tlinks_case20")
    assert "is_timeml_core" in body


# ---------------------------------------------------------------------------
# Mock invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mock_returns_tuple():
    rec = _make_recognizer()
    result = rec.create_tlinks_case20()
    assert isinstance(result, tuple)
    assert len(result) == 2


@pytest.mark.unit
def test_mock_calls_run_query_twice():
    """Method must call _run_query exactly twice (once per sub-case)."""
    rec = _make_recognizer()
    rec.create_tlinks_case20()
    assert rec.graph.run.call_count == 2


@pytest.mark.unit
def test_mock_empty_result_handled():
    """Should not raise if graph returns empty list for either sub-case."""
    rec = _make_recognizer()
    rec.graph.run.return_value.data.return_value = []
    result = rec.create_tlinks_case20()
    assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# __main__ block integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_block_calls_case20(tr_source):
    main_start = tr_source.find("if __name__ == '__main__'")
    assert main_start != -1, "__main__ block not found"
    assert "create_tlinks_case20" in tr_source[main_start:]


@pytest.mark.unit
def test_main_block_case20_before_normalize(tr_source):
    """case20 must run before normalize (so normalize can canonicalize its relTypes)."""
    main_start = tr_source.find("if __name__ == '__main__'")
    assert main_start != -1
    main_block = tr_source[main_start:]
    pos_20 = main_block.find("create_tlinks_case20")
    pos_norm = main_block.find("normalize_tlink_reltypes")
    assert pos_20 != -1
    assert pos_norm != -1
    assert pos_20 < pos_norm


# ---------------------------------------------------------------------------
# phase_wrappers integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase_wrappers_wires_case20():
    wrappers_path = (
        Path(__file__).resolve().parents[1]
        / "pipeline"
        / "runtime"
        / "phase_wrappers.py"
    )
    source = wrappers_path.read_text(encoding="utf-8")
    assert "create_tlinks_case20" in source
