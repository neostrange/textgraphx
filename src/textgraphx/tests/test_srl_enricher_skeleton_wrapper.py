"""Compatibility tests for the moved SRL enricher skeleton module."""

import importlib
import sys
import types


def _install_srl_enricher_skeleton_stubs(monkeypatch):
    text_processor_module = types.ModuleType("textgraphx.TextProcessor")

    class _FakeNeo4jRepository:
        def __init__(self, driver=None):
            self.driver = driver

    text_processor_module.Neo4jRepository = _FakeNeo4jRepository
    monkeypatch.setitem(sys.modules, "textgraphx.TextProcessor", text_processor_module)

    graph_db_base_module = types.ModuleType("textgraphx.util.GraphDbBase")

    class _FakeGraphDBBase:
        pass

    graph_db_base_module.GraphDBBase = _FakeGraphDBBase
    monkeypatch.setitem(sys.modules, "textgraphx.util.GraphDbBase", graph_db_base_module)


def test_srl_enricher_skeleton_module_aliases_canonical_module(monkeypatch):
    _install_srl_enricher_skeleton_stubs(monkeypatch)

    sys.modules.pop("textgraphx.text_processing_components.llm.srl_enricher_skeleton", None)
    sys.modules.pop("textgraphx.SRLEnricher_skeleton", None)

    canonical_module = importlib.import_module("textgraphx.text_processing_components.llm.srl_enricher_skeleton")
    legacy_module = importlib.import_module("textgraphx.SRLEnricher_skeleton")

    assert legacy_module is canonical_module
    assert legacy_module.SRLEnricher is canonical_module.SRLEnricher