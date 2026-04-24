"""Compatibility tests for the moved TextProcessor module."""

import importlib
import sys
import types


def _install_textprocessor_import_stubs(monkeypatch):
    gputil_module = types.ModuleType("GPUtil")
    monkeypatch.setitem(sys.modules, "GPUtil", gputil_module)

    transformers_module = types.ModuleType("transformers")
    transformers_logging = types.SimpleNamespace(set_verbosity_error=lambda: None)
    transformers_module.logging = transformers_logging
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)


def test_textprocessor_module_aliases_canonical_module(monkeypatch):
    _install_textprocessor_import_stubs(monkeypatch)

    sys.modules.pop("textgraphx.pipeline.ingestion.text_processor", None)
    sys.modules.pop("textgraphx.pipeline.ingestion.text_processor", None)

    canonical_module = importlib.import_module("textgraphx.pipeline.ingestion.text_processor")
    legacy_module = importlib.import_module("textgraphx.pipeline.ingestion.text_processor")

    assert legacy_module is canonical_module
    assert legacy_module.TextProcessor is canonical_module.TextProcessor
    assert legacy_module.Neo4jRepository is canonical_module.Neo4jRepository
    assert legacy_module.filter_spans is canonical_module.filter_spans