"""Unit tests for TextProcessor modularization (Iteration 3 item 9)."""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

spacy = pytest.importorskip("spacy", reason="spaCy required for TextProcessor import")


@pytest.mark.unit
class TestTextProcessorFactoryWiring:
    def _fake_components(self):
        return SimpleNamespace(
            wsd=MagicMock(),
            wn_token_enricher=MagicMock(),
            coref=MagicMock(),
            srl_processor=MagicMock(),
            sentence_creator=MagicMock(),
            tag_occurrence_creator=MagicMock(),
            tag_occurrence_dependency_processor=MagicMock(),
            tag_occurrence_query_executor=MagicMock(),
            noun_chunk_processor=MagicMock(),
            entity_processor=MagicMock(),
            entity_fuser=MagicMock(),
            entity_disambiguator=MagicMock(),
        )

    def test_constructor_uses_component_factory(self):
        fake_components = self._fake_components()
        fake_driver = MagicMock()
        fake_nlp = MagicMock()

        with patch("textgraphx.infrastructure.config.get_config") as gc, patch(
            "textgraphx.text_processing_components.pipeline.component_factory.TextPipelineComponentFactory.build"
        ) as build:
            gc.return_value = SimpleNamespace(
                neo4j=SimpleNamespace(uri="bolt://localhost:7687", user="neo4j", password="neo4j"),
                services=SimpleNamespace(wsd_url="http://wsd", coref_url="http://coref"),
            )
            build.return_value = fake_components

            from textgraphx.TextProcessor import TextProcessor
            tp = TextProcessor(fake_nlp, fake_driver)

        build.assert_called_once()
        assert tp.wsd is fake_components.wsd
        assert tp.entity_disambiguator is fake_components.entity_disambiguator

    def test_do_wsd_delegates_to_component(self):
        fake_components = self._fake_components()
        fake_driver = MagicMock()
        fake_nlp = MagicMock()

        with patch("textgraphx.infrastructure.config.get_config") as gc, patch(
            "textgraphx.text_processing_components.pipeline.component_factory.TextPipelineComponentFactory.build"
        ) as build:
            gc.return_value = SimpleNamespace(
                neo4j=SimpleNamespace(uri="bolt://localhost:7687", user="neo4j", password="neo4j"),
                services=SimpleNamespace(wsd_url="http://wsd", coref_url="http://coref"),
            )
            build.return_value = fake_components

            from textgraphx.TextProcessor import TextProcessor
            tp = TextProcessor(fake_nlp, fake_driver)
            tp.do_wsd("doc1")

        fake_components.wsd.perform_wsd.assert_called_once_with("doc1")
