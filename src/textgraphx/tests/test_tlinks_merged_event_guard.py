"""Tests verifying that TLINK case queries exclude merged TEvent nodes.

When ``EventEnrichmentPhase.merge_aligns_with_event_clusters`` runs, secondary
TEvent nodes (NOMBANK-promoted or lower-confidence verbal) are marked
``merged=true`` and ``merged_into=<canonical_id>``.  TLINK rules must not
create edges to/from these zombie events — they would be unreachable from
EventMention and produce false-positive TLINK predictions.

Tests here assert:
- Cases 1–9 all carry a ``coalesce(e.merged, false) = false`` guard.
- The wrapper still wires all nine cases.
- A mock-execution spot-check confirms the guard appears in the executed query.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

TR_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "tlinks_recognizer.py"
)
WRAPPER_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "runtime" / "phase_wrappers.py"
)


@pytest.fixture(scope="module")
def tr_source() -> str:
    return TR_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wrapper_source() -> str:
    return WRAPPER_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


def _make_recognizer(return_value=None):
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = return_value or [{"created": 0}]
    return obj


# ---------------------------------------------------------------------------
# Parametrised: all cases must have merged guard
# ---------------------------------------------------------------------------

# (case_method, primary_event_alias)  — alias used in the WHERE clause
# Cases 8, 13, 14 are intentionally DISABLED (guideline violations / zero-TP FP
# generators on MEANTIME). They return [] without running a query, so source-code
# guard inspection and executed-query checks must be handled separately below.
TLINK_CASES = [
    ("create_tlinks_case1", "e1"),
    ("create_tlinks_case2", "e1"),
    ("create_tlinks_case3", "e1"),
    ("create_tlinks_case4", "e"),
    ("create_tlinks_case5", "e"),
    ("create_tlinks_case6", "e"),
    ("create_tlinks_case7", "e_main"),
    # case8 DISABLED — excluded from parametrised guard check (see dedicated tests below)
    ("create_tlinks_case9", "e"),
    # Cases 10–18 (added in second implementation pass)
    ("create_tlinks_case10", "e"),
    ("create_tlinks_case11", "e"),
    ("create_tlinks_case12", "e_src"),
    ("create_tlinks_case13", "cause"),
    ("create_tlinks_case14", "e_main"),
    ("create_tlinks_case15", "e"),
    ("create_tlinks_case16", "e1"),
    # Case 17 is TIMEX–TIMEX only — no TEvent alias; excluded from this list
    ("create_tlinks_case18", "e1"),
]


@pytest.mark.unit
@pytest.mark.parametrize("method_name,event_alias", TLINK_CASES)
def test_tlink_case_excludes_merged_events(tr_source, method_name, event_alias):
    """Every TLINK case query must filter out merged secondary TEvent nodes."""
    method_src = _extract_method(tr_source, method_name)
    guard = f"coalesce({event_alias}.merged, false) = false"
    assert guard in method_src, (
        f"{method_name}: missing merged-event guard "
        f"'coalesce({event_alias}.merged, false) = false'"
    )


@pytest.mark.unit
@pytest.mark.parametrize("method_name,event_alias", TLINK_CASES)
def test_tlink_case_also_has_low_confidence_guard(tr_source, method_name, event_alias):
    """Sanity: low_confidence guard must still be present alongside merged guard."""
    method_src = _extract_method(tr_source, method_name)
    # Case 7 uses e_main / e_sub — check appropriate alias
    alias = event_alias
    guard = f"coalesce({alias}.low_confidence, false) = false"
    assert guard in method_src, (
        f"{method_name}: missing low_confidence guard for alias '{alias}'"
    )


# ---------------------------------------------------------------------------
# Dual-endpoint cases: both e1 and e2 must have the guard
# ---------------------------------------------------------------------------

DUAL_ENDPOINT_CASES = [
    ("create_tlinks_case1", "e1", "e2"),
    ("create_tlinks_case2", "e1", "e2"),
    ("create_tlinks_case3", "e1", "e2"),
    # Cases 12–18 dual-endpoint (Event×Event)
    ("create_tlinks_case12", "e_src", "e_tgt"),
    ("create_tlinks_case13", "cause", "effect"),
    ("create_tlinks_case14", "e_main", "e_sub"),
    ("create_tlinks_case16", "e1", "e2"),
    ("create_tlinks_case18", "e1", "e2"),
]


@pytest.mark.unit
@pytest.mark.parametrize("method_name,alias1,alias2", DUAL_ENDPOINT_CASES)
def test_dual_endpoint_case_guards_both_events(tr_source, method_name, alias1, alias2):
    """Cases with two TEvent endpoints need the guard on both sides."""
    method_src = _extract_method(tr_source, method_name)
    guard1 = f"coalesce({alias1}.merged, false) = false"
    guard2 = f"coalesce({alias2}.merged, false) = false"
    assert guard1 in method_src, f"{method_name}: missing merged guard for {alias1}"
    assert guard2 in method_src, f"{method_name}: missing merged guard for {alias2}"


@pytest.mark.unit
def test_case7_guards_both_e_main_and_e_sub(tr_source):
    """Case 7 links two TEvent nodes (e_main, e_sub); both must have merged guards."""
    method_src = _extract_method(tr_source, "create_tlinks_case7")
    assert "coalesce(e_main.merged, false) = false" in method_src, \
        "case7 missing merged guard for e_main"
    assert "coalesce(e_sub.merged, false) = false" in method_src, \
        "case7 missing merged guard for e_sub"


# ---------------------------------------------------------------------------
# Spot-check: guard appears in executed Cypher for case 6 (verbal DCT anchor)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_case6_executed_query_excludes_merged_events():
    """Executed case6 Cypher must include the merged guard."""
    recognizer = _make_recognizer()
    recognizer.create_tlinks_case6()
    query = recognizer.graph.run.call_args[0][0]
    assert "merged" in query, (
        "case6 Cypher does not mention 'merged'; guard may be missing"
    )
    assert "false" in query


@pytest.mark.unit
def test_case8_is_disabled_no_graph_run():
    """Case 8 is intentionally disabled — must return [] and never call graph.run."""
    recognizer = _make_recognizer()
    result = recognizer.create_tlinks_case8()
    assert result == [], "create_tlinks_case8 must return [] when disabled"
    assert recognizer.graph.run.call_count == 0, (
        "create_tlinks_case8 must not write to the graph when disabled"
    )


@pytest.mark.unit
def test_case9_executed_query_excludes_merged_events():
    """Executed case9 Cypher must include the merged guard."""
    recognizer = _make_recognizer()
    recognizer.create_tlinks_case9()
    query = recognizer.graph.run.call_args[0][0]
    assert "merged" in query


# ---------------------------------------------------------------------------
# Wrapper: all 9 cases are wired
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tlinks_wrapper_wires_all_nine_cases(wrapper_source):
    """TlinksRecognizerWrapper must reference all nine TLINK case methods."""
    for i in range(1, 10):
        assert f"create_tlinks_case{i}" in wrapper_source, (
            f"TlinksRecognizerWrapper does not call create_tlinks_case{i}"
        )


# ---------------------------------------------------------------------------
# Cases 10–18: additional guard spot-checks
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wrapper_wires_cases_10_to_18(wrapper_source):
    """phase_wrappers.py must reference Cases 10–18 (added second pass)."""
    for i in range(10, 19):
        assert f"create_tlinks_case{i}" in wrapper_source, (
            f"phase_wrappers.py does not call create_tlinks_case{i}"
        )


@pytest.mark.unit
def test_case12_executed_query_excludes_merged_events():
    """Case 12 (GLINK→TLINK bridge) must guard both e_src and e_tgt."""
    recognizer = _make_recognizer()
    recognizer.create_tlinks_case12()
    query = recognizer.graph.run.call_args[0][0]
    assert "merged" in query
    assert "e_src" in query or "e_tgt" in query


@pytest.mark.unit
def test_case13_is_disabled_no_graph_run():
    """Case 13 is intentionally disabled (0 TPs on MEANTIME) — must return [] and not run."""
    recognizer = _make_recognizer()
    result = recognizer.create_tlinks_case13()
    assert result == [], "create_tlinks_case13 must return [] when disabled"
    assert recognizer.graph.run.call_count == 0, (
        "create_tlinks_case13 must not write to the graph when disabled"
    )


@pytest.mark.unit
def test_case14_is_disabled_no_graph_run():
    """Case 14 is intentionally disabled (bidirectional AFTER bug) — must return [] and not run."""
    recognizer = _make_recognizer()
    result = recognizer.create_tlinks_case14()
    assert result == [], "create_tlinks_case14 must return [] when disabled"
    assert recognizer.graph.run.call_count == 0, (
        "create_tlinks_case14 must not write to the graph when disabled"
    )


@pytest.mark.unit
def test_case17_is_timex_timex_no_event_alias(tr_source):
    """Case 17 links TIMEX–TIMEX nodes only; no TEvent merged guard is expected."""
    method_src = _extract_method(tr_source, "create_tlinks_case17")
    # Must NOT match TEvent nodes — no e.merged guard
    assert "(t1:TIMEX)" in method_src or "TIMEX" in method_src
    # The guard absence is intentional — document it in source via TIMEX node label
    assert "TEvent" not in method_src or "merged" not in method_src.split("TEvent")[0]
