"""Compatibility tests for moved service adapter util modules."""

import importlib
import sys
import types
from types import SimpleNamespace


def _install_service_config_stub(monkeypatch):
    config_module = types.ModuleType("textgraphx.infrastructure.config")
    config_module.get_config = lambda: SimpleNamespace(
        services=SimpleNamespace(
            service_timeout_sec=5,
            srl_url="http://example.test/srl",
            heideltime_url="http://example.test/heideltime",
            coref_url="http://example.test/coref",
        ),
    )
    monkeypatch.setitem(sys.modules, "textgraphx.infrastructure.config", config_module)


def _install_spacy_stubs(monkeypatch):
    class _FakeLanguage:
        @staticmethod
        def factory(*args, **kwargs):
            def _decorator(obj):
                return obj

            return _decorator

    class _FakeDoc:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    class _FakeSpan:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    spacy_module = types.ModuleType("spacy")
    spacy_module.util = object()
    monkeypatch.setitem(sys.modules, "spacy", spacy_module)

    spacy_language_module = types.ModuleType("spacy.language")
    spacy_language_module.Language = _FakeLanguage
    monkeypatch.setitem(sys.modules, "spacy.language", spacy_language_module)

    spacy_tokens_module = types.ModuleType("spacy.tokens")
    spacy_tokens_module.Doc = _FakeDoc
    spacy_tokens_module.Span = _FakeSpan
    monkeypatch.setitem(sys.modules, "spacy.tokens", spacy_tokens_module)


def test_rest_caller_module_aliases_canonical_module(monkeypatch):
    _install_service_config_stub(monkeypatch)

    sys.modules.pop("textgraphx.adapters.rest_caller", None)
    sys.modules.pop("textgraphx.util.RestCaller", None)

    canonical_module = importlib.import_module("textgraphx.adapters.rest_caller")
    legacy_module = importlib.import_module("textgraphx.util.RestCaller")

    assert legacy_module is canonical_module
    assert legacy_module.callAllenNlpApi is canonical_module.callAllenNlpApi


def test_allen_nlp_coref_module_aliases_canonical_module(monkeypatch):
    _install_service_config_stub(monkeypatch)

    sys.modules.pop("textgraphx.adapters.allen_nlp_coref", None)
    sys.modules.pop("textgraphx.util.CallAllenNlpCoref", None)

    canonical_module = importlib.import_module("textgraphx.adapters.allen_nlp_coref")
    legacy_module = importlib.import_module("textgraphx.util.CallAllenNlpCoref")

    assert legacy_module is canonical_module
    assert legacy_module.callAllenNlpCoref is canonical_module.callAllenNlpCoref


def test_entity_fishing_v2_module_aliases_canonical_module(monkeypatch):
    _install_spacy_stubs(monkeypatch)

    sys.modules.pop("textgraphx.adapters.entity_fishing_v2", None)
    sys.modules.pop("textgraphx.util.EntityFishingLinker_v2", None)

    canonical_module = importlib.import_module("textgraphx.adapters.entity_fishing_v2")
    legacy_module = importlib.import_module("textgraphx.util.EntityFishingLinker_v2")

    assert legacy_module is canonical_module
    assert legacy_module.EntityFishing is canonical_module.EntityFishing