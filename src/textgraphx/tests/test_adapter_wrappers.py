"""Compatibility tests for moved adapter-style util modules."""

import importlib
import sys
import types
from types import SimpleNamespace


def _install_graph_db_base_stubs(monkeypatch):
    neo4j_module = types.ModuleType("neo4j")
    neo4j_module.GraphDatabase = SimpleNamespace(driver=lambda *args, **kwargs: object())
    monkeypatch.setitem(sys.modules, "neo4j", neo4j_module)

    config_module = types.ModuleType("textgraphx.config")
    config_module.get_config = lambda: SimpleNamespace(
        neo4j=SimpleNamespace(uri=None, user=None, password=None),
    )
    monkeypatch.setitem(sys.modules, "textgraphx.config", config_module)


def _install_spacy_stubs(monkeypatch):
    class _FakeLanguage:
        @staticmethod
        def has_factory(_name):
            return True

        @staticmethod
        def factory(*args, **kwargs):
            def _decorator(obj):
                return obj

            return _decorator

    class _FakeToken:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    class _FakeDoc:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    class _FakeSpan:
        @staticmethod
        def set_extension(*args, **kwargs):
            return None

    spacy_module = types.ModuleType("spacy")
    spacy_module.Language = _FakeLanguage
    monkeypatch.setitem(sys.modules, "spacy", spacy_module)

    spacy_language_module = types.ModuleType("spacy.language")
    spacy_language_module.Language = _FakeLanguage
    monkeypatch.setitem(sys.modules, "spacy.language", spacy_language_module)

    spacy_tokens_module = types.ModuleType("spacy.tokens")
    spacy_tokens_module.Doc = _FakeDoc
    spacy_tokens_module.Token = _FakeToken
    spacy_tokens_module.Span = _FakeSpan
    monkeypatch.setitem(sys.modules, "spacy.tokens", spacy_tokens_module)

    spacy_matcher_module = types.ModuleType("spacy.matcher")
    spacy_matcher_module.Matcher = object
    spacy_matcher_module.DependencyMatcher = object
    monkeypatch.setitem(sys.modules, "spacy.matcher", spacy_matcher_module)


def _install_semantic_role_labeler_stubs(monkeypatch):
    _install_spacy_stubs(monkeypatch)

    gputil_module = types.ModuleType("GPUtil")
    monkeypatch.setitem(sys.modules, "GPUtil", gputil_module)

    transformers_module = types.ModuleType("transformers")
    transformers_module.logging = SimpleNamespace(set_verbosity_error=lambda: None)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)


def _install_entity_fishing_stubs(monkeypatch):
    _install_spacy_stubs(monkeypatch)


def test_graph_db_base_module_aliases_canonical_module(monkeypatch):
    _install_graph_db_base_stubs(monkeypatch)

    sys.modules.pop("textgraphx.adapters.graph_db_base", None)
    sys.modules.pop("textgraphx.util.GraphDbBase", None)

    canonical_module = importlib.import_module("textgraphx.adapters.graph_db_base")
    legacy_module = importlib.import_module("textgraphx.util.GraphDbBase")

    assert legacy_module is canonical_module
    assert legacy_module.GraphDBBase is canonical_module.GraphDBBase


def test_semantic_role_labeler_module_aliases_canonical_module(monkeypatch):
    _install_semantic_role_labeler_stubs(monkeypatch)

    sys.modules.pop("textgraphx.adapters.semantic_role_labeler", None)
    sys.modules.pop("textgraphx.util.SemanticRoleLabeler", None)

    canonical_module = importlib.import_module("textgraphx.adapters.semantic_role_labeler")
    legacy_module = importlib.import_module("textgraphx.util.SemanticRoleLabeler")

    assert legacy_module is canonical_module
    assert legacy_module.SemanticRoleLabel is canonical_module.SemanticRoleLabel


def test_entity_fishing_module_aliases_canonical_module(monkeypatch):
    _install_entity_fishing_stubs(monkeypatch)

    sys.modules.pop("textgraphx.adapters.entity_fishing", None)
    sys.modules.pop("textgraphx.util.EntityFishingLinker", None)

    canonical_module = importlib.import_module("textgraphx.adapters.entity_fishing")
    legacy_module = importlib.import_module("textgraphx.util.EntityFishingLinker")

    assert legacy_module is canonical_module
    assert legacy_module.EntityFishing is canonical_module.EntityFishing
