"""Phase-B unit tests for TimeML relation normalization utilities."""

import pytest


@pytest.mark.unit
def test_normalize_tlink_reltype_passes_canonical_values():
    from textgraphx.reasoning.temporal.timeml_relations import normalize_tlink_reltype

    assert normalize_tlink_reltype("BEFORE") == "BEFORE"
    assert normalize_tlink_reltype("IS_INCLUDED") == "IS_INCLUDED"
    assert normalize_tlink_reltype("VAGUE") == "VAGUE"


@pytest.mark.unit
def test_normalize_tlink_reltype_maps_common_aliases():
    from textgraphx.reasoning.temporal.timeml_relations import normalize_tlink_reltype

    assert normalize_tlink_reltype("include") == "INCLUDES"
    assert normalize_tlink_reltype("included") == "IS_INCLUDED"
    assert normalize_tlink_reltype("measure") == "DURING"
    assert normalize_tlink_reltype("equal") == "IDENTITY"


@pytest.mark.unit
def test_normalize_tlink_reltype_unknown_defaults_to_vague():
    from textgraphx.reasoning.temporal.timeml_relations import normalize_tlink_reltype

    assert normalize_tlink_reltype("RANDOM_LABEL") == "VAGUE"
    assert normalize_tlink_reltype(None) == "VAGUE"
