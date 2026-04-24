"""Compatibility tests for the moved shared constants module."""

import textgraphx.constants as legacy_constants
import textgraphx.schema.constants as canonical_constants


def test_constants_wrapper_reexports_canonical_values():
    assert legacy_constants.LABEL_TEVENT == canonical_constants.LABEL_TEVENT
    assert legacy_constants.REL_TLINK == canonical_constants.REL_TLINK
    assert legacy_constants.PROP_DOC_ID == canonical_constants.PROP_DOC_ID