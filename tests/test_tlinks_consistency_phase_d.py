"""Phase-D tests for TLINK consistency suppression behavior."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_tlinks_recognizer_runs_conflict_suppression_query():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"suppressed": 3}]

    rows = obj.suppress_tlink_conflicts()

    assert rows[0]["suppressed"] == 3
    assert obj.graph.run.called
    query = obj.graph.run.call_args[0][0]
    assert "suppressedBy = 'tlink_consistency_filter'" in query
    assert "suppressionReason" in query


@pytest.mark.unit
def test_tlinks_wrapper_source_includes_conflict_suppression_call():
    from pathlib import Path

    src = Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")
    assert "Suppress contradictory TLINKs" in src
    assert "recognizer.suppress_tlink_conflicts()" in src
    assert "suppressed_tlinks" in src
