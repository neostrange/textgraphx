"""Compatibility tests for the reasoning contracts wrapper."""

import pytest

from textgraphx.reasoning.contracts import (
    canonical_event_attribute_vocabulary as canonical_event_attribute_vocabulary_impl,
    normalize_event_attr as canonical_normalize_event_attr,
)
from textgraphx.reasoning.contracts import canonical_event_attribute_vocabulary, normalize_event_attr


pytestmark = [pytest.mark.unit]


def test_root_reasoning_contracts_wrapper_reexports_canonical_normalizer():
    assert normalize_event_attr is canonical_normalize_event_attr


def test_canonical_reasoning_contracts_reads_ontology_from_parent_schema_dir():
    vocabulary = canonical_event_attribute_vocabulary_impl()
    assert vocabulary == canonical_event_attribute_vocabulary()
    assert "tense" in vocabulary