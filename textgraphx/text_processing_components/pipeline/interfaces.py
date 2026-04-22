"""Explicit interfaces for TextProcessor stage services.

These Protocols document the orchestration contract used by TextProcessor so
component implementations can evolve independently without breaking callers.
"""

from __future__ import annotations

from typing import Any, List, Protocol, Sequence


class SentenceCreatorLike(Protocol):
    def create_sentence_node(
        self,
        annotated_text: Any,
        text_id: Any,
        sentence_id: int,
        sentence: Any,
    ) -> Sequence[Any]:
        ...


class TagOccurrenceCreatorLike(Protocol):
    def create_tag_occurrences(self, sentence: Any, text_id: Any, sentence_id: int) -> List[dict]:
        ...


class TagOccurrenceQueryExecutorLike(Protocol):
    def execute_tag_occurrence_query(self, tag_occurrences: List[dict], sentence_id: Any) -> Any:
        ...


class TagOccurrenceDependencyProcessorLike(Protocol):
    def create_tag_occurrence_dependencies(self, sentence: Any, text_id: Any, sentence_id: int) -> List[dict]:
        ...

    def process_dependencies(self, tag_occurrences: List[dict]) -> Any:
        ...


class NounChunkProcessorLike(Protocol):
    def process_noun_chunks(self, doc: Any, text_id: Any) -> Any:
        ...


class EntityProcessorLike(Protocol):
    def process_entities(self, doc: Any, text_id: Any) -> Any:
        ...


class EntityFuserLike(Protocol):
    def fuse_entities(self, text_id: Any) -> Any:
        ...


class EntityDisambiguatorLike(Protocol):
    def disambiguate_entities(self, text_id: Any) -> Any:
        ...


class WSDLike(Protocol):
    def perform_wsd(self, text_id: Any) -> Any:
        ...


class CoreferenceResolverLike(Protocol):
    def resolve(self, *args: Any, **kwargs: Any) -> Any:
        ...


class SRLProcessorLike(Protocol):
    def process(self, *args: Any, **kwargs: Any) -> Any:
        ...
