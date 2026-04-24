"""Compatibility tests for the moved text-normalization helpers."""

from textgraphx.pipeline.ingestion import text_normalization as canonical_text_normalization
from textgraphx.pipeline.ingestion.text_normalization import normalize_naf_raw_text


def test_text_normalization_wrapper_reexports_canonical_function():
    assert normalize_naf_raw_text is canonical_text_normalization.normalize_naf_raw_text