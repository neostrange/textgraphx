"""Phase-0 tests for EventEnrichment conflict-resolution helpers."""

import sys
import types

import pytest


def _stub_event_enrichment_imports():
    if "spacy" not in sys.modules:
        spacy_mod = types.ModuleType("spacy")
        spacy_mod.load = lambda *args, **kwargs: None
        sys.modules["spacy"] = spacy_mod

    if "spacy.tokens" not in sys.modules:
        tokens_mod = types.ModuleType("spacy.tokens")
        tokens_mod.Doc = object
        tokens_mod.Token = object
        tokens_mod.Span = object
        sys.modules["spacy.tokens"] = tokens_mod

    for mod_name, attrs in (
        ("textgraphx.util.SemanticRoleLabeler", {"SemanticRoleLabel": object}),
        ("textgraphx.util.EntityFishingLinker", {"EntityFishing": object}),
        ("textgraphx.util.GraphDbBase", {"GraphDBBase": object}),
        ("textgraphx.TextProcessor", {"TextProcessor": object}),
    ):
        if mod_name not in sys.modules:
            module = types.ModuleType(mod_name)
            for key, value in attrs.items():
                setattr(module, key, value)
            sys.modules[mod_name] = module


@pytest.mark.unit
def test_tevent_field_defaults_are_primary_temporal():
    _stub_event_enrichment_imports()
    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

    source, confidence = EventEnrichmentPhase._tevent_field_defaults("time")
    assert source == "temporal_phase"
    assert confidence >= 0.9


@pytest.mark.unit
def test_resolve_tevent_field_conflicts_rejects_unsupported_field():
    _stub_event_enrichment_imports()
    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

    phase = EventEnrichmentPhase.__new__(EventEnrichmentPhase)
    phase.graph = None

    with pytest.raises(ValueError):
        phase._resolve_tevent_field_conflicts("unsupported")
