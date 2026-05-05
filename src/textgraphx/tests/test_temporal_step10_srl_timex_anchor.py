"""Tests for Step 10: anchor_srl_timex_candidates_to_events.

Verifies source structure and mock-based behaviour of the new
anchor_srl_timex_candidates_to_events method in TemporalPhase.

Guards verified:
- Matches SRLTimexCandidate nodes with source_fa_id
- Follows FrameArgument → Frame → TEvent (non-provisional frame, non-merged event)
- MERGE HAS_TIME_ANCHOR edge with correct provenance
- rule_id = 'anchor_srl_timex_candidates_v1'
- confidence = 0.65
- Exception safety — returns 0 on failure
- Wired in phase_wrappers after promote_argm_tmp_to_timex_candidates
- Wired in __main__ block

No live Neo4j required.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

TEMPORAL_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "temporal.py"
)


@pytest.fixture(scope="module")
def tp_source() -> str:
    return TEMPORAL_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"{method_name!r} not found in source"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


@pytest.fixture(scope="module")
def method_src(tp_source):
    return _extract_method(tp_source, "anchor_srl_timex_candidates_to_events")


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(tp_source):
    assert "def anchor_srl_timex_candidates_to_events" in tp_source


# ---------------------------------------------------------------------------
# Query: SRLTimexCandidate input
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_matches_srl_timex_candidate(method_src):
    assert "SRLTimexCandidate" in method_src


@pytest.mark.unit
def test_uses_source_fa_id(method_src):
    assert "source_fa_id" in method_src


# ---------------------------------------------------------------------------
# Query: provenance chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_matches_frame_argument(method_src):
    assert ":FrameArgument" in method_src


@pytest.mark.unit
def test_matches_frame(method_src):
    assert ":Frame" in method_src


@pytest.mark.unit
def test_provisional_frame_guard(method_src):
    assert "provisional" in method_src


@pytest.mark.unit
def test_canonical_event_guard(method_src):
    assert "merged" in method_src


# ---------------------------------------------------------------------------
# Query: MERGE HAS_TIME_ANCHOR
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_merges_has_time_anchor(method_src):
    assert "HAS_TIME_ANCHOR" in method_src


@pytest.mark.unit
def test_confidence_is_0_65(method_src):
    assert "0.65" in method_src


@pytest.mark.unit
def test_rule_id_set(method_src):
    assert "anchor_srl_timex_candidates_v1" in method_src


@pytest.mark.unit
def test_source_property_set(method_src):
    assert "srl_argm_tmp_anchor" in method_src


# ---------------------------------------------------------------------------
# Exception safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_exception_safety(method_src):
    assert "except Exception" in method_src
    assert "return 0" in method_src


# ---------------------------------------------------------------------------
# Wiring: phase_wrappers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_phase_wrappers():
    wrappers_path = TEMPORAL_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    assert "anchor_srl_timex_candidates_to_events" in src


@pytest.mark.unit
def test_wired_after_promote_argm_tmp_in_wrappers():
    wrappers_path = TEMPORAL_PATH.parents[2] / "pipeline" / "runtime" / "phase_wrappers.py"
    src = wrappers_path.read_text(encoding="utf-8")
    promote_pos = src.find("promote_argm_tmp_to_timex_candidates")
    anchor_pos = src.find("anchor_srl_timex_candidates_to_events")
    assert promote_pos != -1 and anchor_pos != -1
    assert anchor_pos > promote_pos, "anchor step must follow promote_argm_tmp step"


# ---------------------------------------------------------------------------
# Wiring: __main__
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wired_in_main_block(tp_source):
    main_start = tp_source.find("if __name__ == '__main__':")
    assert main_start != -1
    main_block = tp_source[main_start:]
    assert "anchor_srl_timex_candidates_to_events" in main_block


@pytest.mark.unit
def test_wired_after_promote_in_main(tp_source):
    main_start = tp_source.find("if __name__ == '__main__':")
    main_block = tp_source[main_start:]
    promote_pos = main_block.find("promote_argm_tmp_to_timex_candidates")
    anchor_pos = main_block.find("anchor_srl_timex_candidates_to_events")
    assert promote_pos != -1 and anchor_pos != -1
    assert anchor_pos > promote_pos


# ---------------------------------------------------------------------------
# Mock-based behaviour
# ---------------------------------------------------------------------------


def _make_phase(rows):
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    phase = TemporalPhase.__new__(TemporalPhase)
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = rows
    phase.graph = mock_graph
    return phase


@pytest.mark.unit
def test_returns_anchored_count():
    phase = _make_phase([{"anchored": 4}])
    result = phase.anchor_srl_timex_candidates_to_events("doc1")
    assert result == 4


@pytest.mark.unit
def test_returns_zero_when_no_rows():
    phase = _make_phase([])
    result = phase.anchor_srl_timex_candidates_to_events("doc1")
    assert result == 0


@pytest.mark.unit
def test_returns_zero_on_exception():
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    phase = TemporalPhase.__new__(TemporalPhase)
    mock_graph = MagicMock()
    mock_graph.run.side_effect = RuntimeError("db offline")
    phase.graph = mock_graph
    assert phase.anchor_srl_timex_candidates_to_events("doc1") == 0


@pytest.mark.unit
def test_passes_doc_id_as_parameter():
    from textgraphx.pipeline.phases.temporal import TemporalPhase

    phase = TemporalPhase.__new__(TemporalPhase)
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = [{"anchored": 2}]
    phase.graph = mock_graph
    phase.anchor_srl_timex_candidates_to_events("doc42")
    call_kwargs = mock_graph.run.call_args
    # parameters dict must contain the doc_id
    params = call_kwargs[1].get("parameters") or (call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
    assert params.get("doc_id") == "doc42" or "doc42" in str(call_kwargs)
