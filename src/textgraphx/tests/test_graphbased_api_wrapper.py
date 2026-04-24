"""Compatibility tests for the moved legacy GraphBasedNLP API module."""

import importlib
import sys
import types


def test_graphbased_api_module_aliases_canonical_module(monkeypatch):
    class FakeGraphBasedNLP:
        def __init__(self, argv):
            self.argv = argv

        def store_corpus(self, directory):
            return [(directory,)]

        def process_text(self, *args, **kwargs):
            return None

        def execute_cypher_query(self, query):
            return [query]

    fake_graphbased_module = types.ModuleType("textgraphx.pipeline.ingestion.graph_based_nlp")
    fake_graphbased_module.GraphBasedNLP = FakeGraphBasedNLP
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.ingestion.graph_based_nlp", fake_graphbased_module)

    sys.modules.pop("textgraphx.infrastructure.graphbased_api", None)
    sys.modules.pop("textgraphx.infrastructure.graphbased_api", None)

    canonical_api = importlib.import_module("textgraphx.infrastructure.graphbased_api")
    legacy_api = importlib.import_module("textgraphx.infrastructure.graphbased_api")

    assert legacy_api is canonical_api
    assert legacy_api.app is canonical_api.app
