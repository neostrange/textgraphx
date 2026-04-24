"""Compatibility tests for the moved SRL enricher skeleton module."""

import importlib
import sys
import types


def _install_srl_enricher_skeleton_stubs(monkeypatch):
    # Drop any leaked aliases from prior tests that may have bound legacy
    # ``textgraphx.TextProcessor`` to a stale fake module. We then ensure the
    # canonical text_processor is loaded fresh and the legacy shim re-aliases
    # to it before installing our own fake stub via monkeypatch.
    for stale in (
        "textgraphx.TextProcessor",
        "textgraphx.pipeline.ingestion.text_processor",
        "textgraphx.GraphBasedNLP",
        "textgraphx.pipeline.ingestion.graph_based_nlp",
    ):
        sys.modules.pop(stale, None)
    importlib.import_module("textgraphx.pipeline.ingestion.text_processor")
    importlib.import_module("textgraphx.TextProcessor")

    text_processor_module = types.ModuleType("textgraphx.pipeline.ingestion.text_processor")

    class _FakeNeo4jRepository:
        def __init__(self, driver=None):
            self.driver = driver

    text_processor_module.Neo4jRepository = _FakeNeo4jRepository
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.ingestion.text_processor", text_processor_module)

    graph_db_base_module = types.ModuleType("textgraphx.util.GraphDbBase")

    class _FakeGraphDBBase:
        pass

    graph_db_base_module.GraphDBBase = _FakeGraphDBBase
    monkeypatch.setitem(sys.modules, "textgraphx.util.GraphDbBase", graph_db_base_module)


def test_srl_enricher_skeleton_module_aliases_canonical_module(monkeypatch):
    _install_srl_enricher_skeleton_stubs(monkeypatch)

    sys.modules.pop("textgraphx.text_processing_components.llm.srl_enricher_skeleton", None)
    sys.modules.pop("textgraphx.text_processing_components.llm.srl_enricher_skeleton", None)

    try:
        canonical_module = importlib.import_module("textgraphx.text_processing_components.llm.srl_enricher_skeleton")
        legacy_module = importlib.import_module("textgraphx.text_processing_components.llm.srl_enricher_skeleton")

        assert legacy_module is canonical_module
    finally:
        # Clear any modules that may have aliased the fake text_processor stub
        # so that subsequent tests get a fresh import of the real canonical module.
        for name in (
            "textgraphx.TextProcessor",
            "textgraphx.GraphBasedNLP",
            "textgraphx.text_processing_components.llm.srl_enricher_skeleton",
            "textgraphx.text_processing_components.llm.srl_enricher_skeleton",
            "textgraphx.pipeline.ingestion.graph_based_nlp",
        ):
            sys.modules.pop(name, None)
    assert legacy_module.SRLEnricher is canonical_module.SRLEnricher