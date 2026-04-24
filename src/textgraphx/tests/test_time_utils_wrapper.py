"""Compatibility tests for the moved time utils helpers."""

import textgraphx.time_utils as legacy_time_utils
from textgraphx.reasoning.temporal import time as canonical_time_utils


def test_time_utils_wrapper_reexports_canonical_functions():
    assert legacy_time_utils.utc_iso_now is canonical_time_utils.utc_iso_now
    assert legacy_time_utils.utc_timestamp_now is canonical_time_utils.utc_timestamp_now