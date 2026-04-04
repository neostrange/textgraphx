from textgraphx.evaluation.meantime_evaluator import _canonicalize_timex_attrs


def test_canonicalize_timex_attrs_normalizes_compact_date_value():
    attrs = dict(
        _canonicalize_timex_attrs(
            {
                "type": "DATE",
                "value": "20070810",
                "functionInDocument": "NONE",
            }
        )
    )

    assert attrs == {
        "functionInDocument": "NONE",
        "type": "DATE",
        "value": "2007-08-10",
    }


def test_canonicalize_timex_attrs_defaults_function_in_document():
    attrs = dict(
        _canonicalize_timex_attrs(
            {
                "type": "date",
                "value": "2007-08-10",
                "functionInDocument": "",
            }
        )
    )

    assert attrs == {
        "functionInDocument": "NONE",
        "type": "DATE",
        "value": "2007-08-10",
    }