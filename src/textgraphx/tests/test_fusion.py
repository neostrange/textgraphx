"""Unit/regression tests for Iteration 4.15 fusion utilities."""

import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path

from textgraphx.fusion import fuse_entities_cross_sentence
from textgraphx.reasoning.fusion import (
    fuse_entities_cross_sentence as canonical_fuse_entities_cross_sentence,
)

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_root_fusion_wrapper_reexports_canonical_cross_sentence_helper():
    assert fuse_entities_cross_sentence is canonical_fuse_entities_cross_sentence


@pytest.mark.unit
class TestFusionUtilities:
    def test_fuse_cross_sentence_executes_query(self):
        from textgraphx.fusion import fuse_entities_cross_sentence

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 4}]

        count = fuse_entities_cross_sentence(graph, doc_id="doc-1")
        assert count == 4
        graph.run.assert_called_once()

    def test_fuse_cross_sentence_without_doc_filter(self):
        from textgraphx.fusion import fuse_entities_cross_sentence

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 0}]
        count = fuse_entities_cross_sentence(graph)
        assert count == 0

    def test_fuse_cross_document_executes_query(self):
        from textgraphx.fusion import fuse_entities_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 2}]

        count = fuse_entities_cross_document(graph)
        assert count == 2
        graph.run.assert_called_once()

    def test_fuse_cross_document_enforces_type_compatibility_by_default(self):
        from textgraphx.fusion import fuse_entities_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]

        fuse_entities_cross_document(graph)

        params = graph.run.call_args[0][1]
        assert params["require_type_compatibility"] is True

    def test_fuse_cross_document_can_disable_type_compatibility(self):
        from textgraphx.fusion import fuse_entities_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]

        fuse_entities_cross_document(graph, require_type_compatibility=False)

        params = graph.run.call_args[0][1]
        assert params["require_type_compatibility"] is False

    def test_invalid_confidence_raises(self):
        from textgraphx.fusion import fuse_entities_cross_document

        graph = MagicMock()
        with pytest.raises(ValueError):
            fuse_entities_cross_document(graph, confidence=1.5)

    def test_coref_identity_cross_document_executes_query(self):
        from textgraphx.fusion import propagate_coreference_identity_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 3}]

        count = propagate_coreference_identity_cross_document(graph)
        assert count == 3
        graph.run.assert_called_once()

    def test_coref_identity_can_disable_type_compatibility(self):
        from textgraphx.fusion import propagate_coreference_identity_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]

        propagate_coreference_identity_cross_document(
            graph,
            require_type_compatibility=False,
            min_key_length=4,
        )

        params = graph.run.call_args[0][1]
        assert params["require_type_compatibility"] is False
        assert params["min_key_length"] == 4


@pytest.mark.regression
class TestFusionContracts:
    def test_cross_sentence_returns_int(self):
        from textgraphx.fusion import fuse_entities_cross_sentence

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]
        assert isinstance(fuse_entities_cross_sentence(graph, doc_id="x"), int)

    def test_cross_document_returns_int(self):
        from textgraphx.fusion import fuse_entities_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 1}]
        assert isinstance(fuse_entities_cross_document(graph), int)

    def test_coref_identity_returns_int(self):
        from textgraphx.fusion import propagate_coreference_identity_cross_document

        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"c": 2}]
        assert isinstance(propagate_coreference_identity_cross_document(graph), int)
