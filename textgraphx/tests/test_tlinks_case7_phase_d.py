"""Phase-D tests for TLINK case7 clause/scope connective family."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_tlinks_recognizer_case7_query_contract():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"created": 0}]

    rows = obj.create_tlinks_case7()

    assert rows[0]["created"] == 0
    query = obj.graph.run.call_args[0][0]
    assert "case7_clause_scope_connective" in query
    assert "temporalCueHeads" in query
    assert "ARGM-TMP" in query


@pytest.mark.unit
def test_tlinks_wrapper_includes_case7():
    src = Path("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py").read_text(encoding="utf-8")

    assert "create_tlinks_case7" in src
    assert "Case 7: Clause/Scope Connective TLINKs" in src
