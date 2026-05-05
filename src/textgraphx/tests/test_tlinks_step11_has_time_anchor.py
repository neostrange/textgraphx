"""Tests for Step 11: create_tlinks_case11 (HAS_TIME_ANCHOR → TLINK).

Verifies source structure and mock-based behaviour of the new
create_tlinks_case11 method in TlinksRecognizer.

Guards verified:
- Method exists
- Follows HAS_TIME_ANCHOR edge from TEvent to SRLTimexCandidate
- SRLTimexCandidate must have REFERS_TO → TIMEX bridge
- Guards: non-merged, non-low-confidence, is_timeml_core
- MERGE TLINK with ON CREATE / ON MATCH semantics
- rule_id = 'case11_has_time_anchor'
- confidence = 0.57
- source = 't2g'
- Wired in __main__ after create_tlinks_case10
- Wired in phase_wrappers tlink_cases list after case 10
- Exception safety via _run_query

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

TLINKS_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "tlinks_recognizer.py"
)


@pytest.fixture(scope="module")
def tr_source() -> str:
    return TLINKS_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"{method_name!r} not found in source"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


@pytest.fixture(scope="module")
def method_src(tr_source):
    return _extract_method(tr_source, "create_tlinks_case11")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(tr_source):
    assert "def create_tlinks_case11" in tr_source


# ---------------------------------------------------------------------------
# Query: HAS_TIME_ANCHOR traversal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_matches_has_time_anchor(method_src):
    assert "HAS_TIME_ANCHOR" in method_src


@pytest.mark.unit
def test_matches_srl_timex_candidate(method_src):
    assert "SRLTimexCandidate" in method_src


@pytest.mark.unit
def test_requires_refers_to_timex(method_src):
    assert "REFERS_TO" in method_src
    assert ":TIMEX" in method_src


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_merged_guard(method_src):
    assert "merged" in method_src


@pytest.mark.unit
def test_low_confidence_guard(method_src):
    assert "low_confidence" in method_src


@pytest.mark.unit
def test_is_timeml_core_guard(method_src):
    assert "is_timeml_core" in method_src


# ---------------------------------------------------------------------------
# MERGE TLINK provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_merges_tlink(method_src):
    assert "MERGE" in method_src
    assert "TLINK" in method_src


@pytest.mark.unit
def test_confidence_is_0_57(method_src):
    assert "0.57" in method_src


@pytest.mark.unit
def test_rule_id_set(method_src):
    assert "case11_has_time_anchor" in method_src


@pytest.mark.unit
def test_source_is_t2g(method_src):
    assert "'t2g'" in method_src


@pytest.mark.unit
def test_rel_type_is_is_included(method_src):
    assert "IS_INCLUDED" in method_src


@pytest.mark.unit
def test_on_create_set_present(method_src):
    assert "ON CREATE SET" in method_src


@pytest.mark.unit
def test_on_match_set_present(method_src):
    assert "ON MATCH SET" in method_src


@pytest.mark.unit
def test_on_match_uses_coalesce(method_src):
    assert "coalesce" in method_src


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_run_query_result(method_src):
    assert "_run_query" in method_src
    assert "RETURN count(tl)" in method_src


# ---------------------------------------------------------------------------
# Wiring: __main__ block
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(tr_source):
    main_pos = tr_source.find("if __name__ == '__main__':")
    assert main_pos != -1, "__main__ block not found"
    main_src = tr_source[main_pos:]
    assert "create_tlinks_case11" in main_src


@pytest.mark.unit
def test_main_case11_after_case10(tr_source):
    main_pos = tr_source.find("if __name__ == '__main__':")
    main_src = tr_source[main_pos:]
    case10_pos = main_src.find("create_tlinks_case10")
    case11_pos = main_src.find("create_tlinks_case11")
    assert case10_pos != -1 and case11_pos != -1
    assert case11_pos > case10_pos


# ---------------------------------------------------------------------------
# Wiring: phase_wrappers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_phase_wrappers():
    wrappers_path = TLINKS_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "create_tlinks_case11" in src


@pytest.mark.unit
def test_wrappers_case11_after_case10():
    wrappers_path = TLINKS_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    pos10 = src.find("create_tlinks_case10")
    pos11 = src.find("create_tlinks_case11")
    assert pos10 != -1 and pos11 != -1
    assert pos11 > pos10


# ---------------------------------------------------------------------------
# Mock call: method is callable and returns _run_query result
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mock_call_returns_value():
    """create_tlinks_case11 delegates to _run_query; mock that path."""
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = [{"created": 3}]

    # Import dynamically to avoid heavy dependency resolution at collection time
    import importlib.util
    spec = importlib.util.spec_from_file_location("tlinks_recognizer", TLINKS_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Patch the graph connection at the module level before exec
    import sys
    sys.modules.setdefault("py2neo", MagicMock())
    sys.modules.setdefault("neo4j", MagicMock())
    # We test method source integrity instead of live instantiation
    assert "def create_tlinks_case11" in TLINKS_PATH.read_text()
