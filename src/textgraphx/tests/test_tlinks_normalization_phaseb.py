"""Phase-B unit tests for TlinksRecognizer normalization behavior."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_tlinks_recognizer_runs_normalization_query():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"normalized": 5}]

    rows = obj.normalize_tlink_reltypes()

    assert rows[0]["normalized"] == 5
    assert obj.graph.run.called
    query = obj.graph.run.call_args[0][0]
    params = obj.graph.run.call_args[0][1]
    assert "MATCH ()-[r:TLINK]-()" in query
    assert "relTypeCanonical" in query
    assert "canonical" in params


@pytest.mark.unit
def test_tlinks_wrapper_source_includes_normalization_call():
    from pathlib import Path

    src = (Path(__file__).parent.parent / "phase_wrappers.py").read_text(encoding="utf-8")
    assert "Normalize TLINK relation inventory" in src
    assert "recognizer.normalize_tlink_reltypes()" in src
