"""Compatibility tests for the moved API module."""

import textgraphx.infrastructure.api as legacy_api
from textgraphx.infrastructure import api as canonical_api


def test_api_module_aliases_canonical_module():
    assert legacy_api is canonical_api
    assert legacy_api.app is canonical_api.app