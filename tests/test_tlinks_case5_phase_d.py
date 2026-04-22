"""Phase-D tests for TLINK case5 preposition-to-relType mapping."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_tlinks_recognizer_case5_query_contract_for_by_date_precision():
    from textgraphx.TlinksRecognizer import TlinksRecognizer

    obj = TlinksRecognizer.__new__(TlinksRecognizer)
    obj.graph = MagicMock()
    obj.graph.run.return_value.data.return_value = [{"touched": 0}]

    rows = obj.create_tlinks_case5()

    assert rows[0]["touched"] == 0
    query = obj.graph.run.call_args[0][0]

    assert "case5_timex_preposition" in query
    assert "WHEN t.type = 'DATE' AND prep_head = 'by' AND e.tense IN ['PAST'] THEN 'ENDED_BY'" in query
    assert "WHEN t.type = 'DATE' AND prep_head = 'by' THEN 'BEFORE'" in query

    # Keep stricter ENDED_BY condition ahead of fallback BEFORE for DATE+by.
    assert query.index("WHEN t.type = 'DATE' AND prep_head = 'by' AND e.tense IN ['PAST'] THEN 'ENDED_BY'") < query.index(
        "WHEN t.type = 'DATE' AND prep_head = 'by' THEN 'BEFORE'"
    )
