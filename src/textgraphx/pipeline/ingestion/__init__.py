"""Canonical pipeline ingestion helpers."""

from textgraphx.pipeline.ingestion.text_normalization import normalize_naf_raw_text

__all__ = ["GraphBasedNLP", "TextProcessor", "normalize_naf_raw_text"]


def __getattr__(name: str):
    if name == "GraphBasedNLP":
        from textgraphx.pipeline.ingestion.graph_based_nlp import GraphBasedNLP

        return GraphBasedNLP
    if name == "TextProcessor":
        from textgraphx.pipeline.ingestion.text_processor import TextProcessor

        return TextProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")