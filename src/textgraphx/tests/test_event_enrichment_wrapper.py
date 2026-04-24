"""Compatibility tests for the moved EventEnrichmentPhase module."""

import importlib
import sys
import types


def _install_event_enrichment_import_stubs(monkeypatch):
    spacy_module = types.ModuleType("spacy")
    spacy_module.load = lambda *args, **kwargs: None
    spacy_module.Language = object
    monkeypatch.setitem(sys.modules, "spacy", spacy_module)

    tokens_module = types.ModuleType("spacy.tokens")
    tokens_module.Doc = object
    tokens_module.Token = object
    tokens_module.Span = object
    monkeypatch.setitem(sys.modules, "spacy.tokens", tokens_module)

    matcher_module = types.ModuleType("spacy.matcher")
    matcher_module.Matcher = object
    matcher_module.DependencyMatcher = object
    monkeypatch.setitem(sys.modules, "spacy.matcher", matcher_module)

    language_module = types.ModuleType("spacy.language")
    language_module.Language = object
    monkeypatch.setitem(sys.modules, "spacy.language", language_module)

    for mod_name, attrs in (
        ("textgraphx.util.SemanticRoleLabeler", {"SemanticRoleLabel": object}),
        ("textgraphx.util.EntityFishingLinker", {"EntityFishing": object}),
        ("textgraphx.util.RestCaller", {"callAllenNlpApi": lambda *args, **kwargs: None}),
        ("textgraphx.util.GraphDbBase", {"GraphDBBase": object}),
        ("textgraphx.neo4j_client", {"make_graph_from_config": lambda: None}),
    ):
        module = types.ModuleType(mod_name)
        for key, value in attrs.items():
            setattr(module, key, value)
        monkeypatch.setitem(sys.modules, mod_name, module)


def test_event_enrichment_module_aliases_canonical_module(monkeypatch):
    _install_event_enrichment_import_stubs(monkeypatch)

    sys.modules.pop("textgraphx.pipeline.phases.event_enrichment", None)
    sys.modules.pop("textgraphx.EventEnrichmentPhase", None)

    canonical_module = importlib.import_module("textgraphx.pipeline.phases.event_enrichment")
    legacy_module = importlib.import_module("textgraphx.EventEnrichmentPhase")

    assert legacy_module is canonical_module
    assert legacy_module.EventEnrichmentPhase is canonical_module.EventEnrichmentPhase