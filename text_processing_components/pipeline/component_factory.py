"""Factory for TextProcessor stage components.

Centralizing construction logic keeps TextProcessor focused on orchestration
instead of object wiring details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textgraphx.text_processing_components.WordSenseDisambiguator import WordSenseDisambiguator
from textgraphx.text_processing_components.WordnetTokenEnricher import WordnetTokenEnricher
from textgraphx.text_processing_components.CoreferenceResolver import CoreferenceResolver
from textgraphx.text_processing_components.SRLProcessor import SRLProcessor
from textgraphx.text_processing_components.SentenceCreator import SentenceCreator
from textgraphx.text_processing_components.TagOccurrenceCreator import TagOccurrenceCreator
from textgraphx.text_processing_components.TagOccurrenceDependencyProcessor import TagOccurrenceDependencyProcessor
from textgraphx.text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor
from textgraphx.text_processing_components.NounChunkProcessor import NounChunkProcessor
from textgraphx.text_processing_components.EntityProcessor import EntityProcessor
from textgraphx.text_processing_components.EntityFuser import EntityFuser
from textgraphx.text_processing_components.EntityDisambiguator import EntityDisambiguator


@dataclass
class TextPipelineComponents:
    wsd: Any
    wn_token_enricher: Any
    coref: Any
    srl_processor: Any
    sentence_creator: Any
    tag_occurrence_creator: Any
    tag_occurrence_dependency_processor: Any
    tag_occurrence_query_executor: Any
    noun_chunk_processor: Any
    entity_processor: Any
    entity_fuser: Any
    entity_disambiguator: Any


class TextPipelineComponentFactory:
    """Build concrete component instances for TextProcessor."""

    @staticmethod
    def build(nlp: Any, neo4j_repository: Any, wsd_endpoint: str, coref_endpoint: str) -> TextPipelineComponents:
        return TextPipelineComponents(
            wsd=WordSenseDisambiguator(wsd_endpoint, neo4j_repository),
            wn_token_enricher=WordnetTokenEnricher(neo4j_repository),
            coref=CoreferenceResolver(coref_endpoint),
            srl_processor=SRLProcessor(),
            sentence_creator=SentenceCreator(neo4j_repository),
            tag_occurrence_creator=TagOccurrenceCreator(nlp),
            tag_occurrence_dependency_processor=TagOccurrenceDependencyProcessor(neo4j_repository),
            tag_occurrence_query_executor=TagOccurrenceQueryExecutor(neo4j_repository),
            noun_chunk_processor=NounChunkProcessor(neo4j_repository),
            entity_processor=EntityProcessor(neo4j_repository),
            entity_fuser=EntityFuser(neo4j_repository),
            entity_disambiguator=EntityDisambiguator(neo4j_repository),
        )
