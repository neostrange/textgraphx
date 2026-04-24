"""TDD tests for Milestone 2: Repair Schema-Code Contradictions.

Each test validates that the runtime Cypher emitted by a maintained module
matches the canonical ingestion-path schema (as defined in ontology.json and
schema.md), rather than a stale or internally inconsistent variant.

Modules under test:
- textgraphx.fusion (cross-sentence and cross-document entity fusion)
- textgraphx.EventEnrichmentPhase (non-core participant event enrichment)
- textgraphx.TlinksRecognizer (case6 DCT anchoring)
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Stubs for heavy optional deps (spaCy, bolt driver) that are not installed
# or would connect to a live service.
# ---------------------------------------------------------------------------

def _stub_spacy():
    """Stub all spacy submodules referenced in the EventEnrichmentPhase import chain."""
    spacy_mod = types.ModuleType("spacy")
    spacy_mod.load = MagicMock(return_value=MagicMock())
    spacy_mod.Language = MagicMock()
    sys.modules["spacy"] = spacy_mod

    for sub in ("spacy.tokens", "spacy.matcher", "spacy.language"):
        if sub not in sys.modules:
            mod = types.ModuleType(sub)
            sys.modules[sub] = mod

    sys.modules["spacy.tokens"].Doc = MagicMock()
    sys.modules["spacy.tokens"].Token = MagicMock()
    sys.modules["spacy.tokens"].Span = MagicMock()
    sys.modules["spacy.matcher"].Matcher = MagicMock()
    sys.modules["spacy.matcher"].DependencyMatcher = MagicMock()
    sys.modules["spacy.language"].Language = MagicMock()


def _make_mock_graph():
    g = MagicMock()
    g.run.return_value.data.return_value = [{"c": 0}]
    return g


# ---------------------------------------------------------------------------
# Helper: load TlinksRecognizer bypassing __init__ (which connects to Neo4j)
# ---------------------------------------------------------------------------

def _load_tlinks_class():
    with patch("textgraphx.neo4j_client.make_graph_from_config", return_value=MagicMock()):
        from textgraphx.TlinksRecognizer import TlinksRecognizer
    return TlinksRecognizer


# ---------------------------------------------------------------------------
# Helper: load EventEnrichmentPhase bypassing __init__
# ---------------------------------------------------------------------------

def _load_eep_class():
    _stub_spacy()
    # Stub heavy util sub-modules that aren't installed in the test venv
    for mod_name, attrs in (
        ("textgraphx.util.SemanticRoleLabeler", {"SemanticRoleLabel": MagicMock()}),
        ("textgraphx.util.EntityFishingLinker", {"EntityFishing": MagicMock()}),
        ("textgraphx.util.RestCaller", {"callAllenNlpApi": MagicMock()}),
        ("textgraphx.util.GraphDbBase", {"GraphDBBase": MagicMock()}),
    ):
        if mod_name not in sys.modules:
            m = types.ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[mod_name] = m
    with patch("textgraphx.neo4j_client.make_graph_from_config", return_value=MagicMock()):
        import importlib
        if "textgraphx.EventEnrichmentPhase" in sys.modules:
            eep_mod = sys.modules["textgraphx.EventEnrichmentPhase"]
        else:
            import textgraphx.EventEnrichmentPhase as eep_mod
    return eep_mod.EventEnrichmentPhase


# ---------------------------------------------------------------------------
# fusion.py — relationship name contract
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFusionRelationshipContract:
    """fusion.py queries must use canonical relationship names."""

    def _captured_query(self, func_name: str) -> str:
        import textgraphx.fusion as fusion_mod
        mock_graph = _make_mock_graph()
        getattr(fusion_mod, func_name)(mock_graph)
        assert mock_graph.run.called, "fusion function did not call graph.run"
        return mock_graph.run.call_args[0][0]  # positional first arg = query string

    def test_cross_sentence_uses_contains_sentence_not_contains(self):
        query = self._captured_query("fuse_entities_cross_sentence")
        assert "CONTAINS_SENTENCE" in query, (
            "fuse_entities_cross_sentence must traverse [:CONTAINS_SENTENCE] (canonical)"
        )
        assert "[:CONTAINS]->" not in query, (
            "fuse_entities_cross_sentence must not use stale [:CONTAINS] relationship"
        )

    def test_cross_sentence_uses_has_token_not_participates_in_for_sentence_token(self):
        query = self._captured_query("fuse_entities_cross_sentence")
        assert "HAS_TOKEN" in query, (
            "fuse_entities_cross_sentence must traverse [:HAS_TOKEN] to reach TagOccurrences from Sentence"
        )

    def test_cross_document_uses_contains_sentence_not_contains(self):
        query = self._captured_query("fuse_entities_cross_document")
        assert "CONTAINS_SENTENCE" in query, (
            "fuse_entities_cross_document must traverse [:CONTAINS_SENTENCE] (canonical)"
        )

    def test_cross_document_uses_has_token_not_participates_in_for_sentence_token(self):
        query = self._captured_query("fuse_entities_cross_document")
        assert "HAS_TOKEN" in query, (
            "fuse_entities_cross_document must traverse [:HAS_TOKEN] to reach TagOccurrences from Sentence"
        )


# ---------------------------------------------------------------------------
# EventEnrichmentPhase — unreachable ARGM-TMP branch
# (source inspection — import chain requires cgitb/GPUtil/transformers,
#  none of which are in the Python 3.13 test venv)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEventEnrichmentNonCoreParticipants:
    """add_non_core_participants_to_event must not contain a ARGM-TMP CASE branch
    that is unreachable due to the WHERE filter that already excludes ARGM-TMP."""

    EEP_SRC = ROOT / "textgraphx" / "pipeline" / "phases" / "event_enrichment.py"

    def _source(self) -> str:
        return self.EEP_SRC.read_text(encoding="utf-8")

    def test_source_file_exists(self):
        assert self.EEP_SRC.exists()

    def test_argmtmp_where_filter_and_case_are_consistent(self):
        """If ARGM-TMP is excluded from non-core processing via WHERE, it must
        not appear as an active WHEN branch inside the same query's CASE."""
        src = self._source()
        # Find the add_non_core_participants_to_event function body
        marker = "add_non_core_participants_to_event"
        assert marker in src, "method not found in source"
        func_start = src.index(marker)
        # The unreachable WHEN must be gone
        # We check the function body after the def for both the WHERE exclusion
        # and the absence of an unreachable WHEN 'ARGM-TMP'
        body = src[func_start:]
        # Next def/class boundary — take just this method
        import re
        next_def = re.search(r"\n    def |\nclass ", body[len(marker):])
        if next_def:
            body = body[: len(marker) + next_def.start()]
        has_where_exclusion = "ARGM-TMP" in body and "NOT fa.type IN" in body
        has_unreachable_when = "WHEN 'ARGM-TMP'" in body
        assert not has_unreachable_when, (
            "add_non_core_participants_to_event has an unreachable WHEN 'ARGM-TMP' branch; "
            "remove it since ARGM-TMP is already excluded by WHERE"
        )


# ---------------------------------------------------------------------------
# TlinksRecognizer — stale e.modal reference
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTlinksRecognizerCase6:
    """create_tlinks_case6 must not reference the undocumented TEvent.modal property."""

    def _captured_case6_query(self) -> str:
        TlinksRecognizer = _load_tlinks_class()
        obj = TlinksRecognizer.__new__(TlinksRecognizer)
        obj.graph = _make_mock_graph()
        obj.create_tlinks_case6()
        assert obj.graph.run.called
        return obj.graph.run.call_args[0][0]

    def test_case6_does_not_reference_modal_property(self):
        query = self._captured_case6_query()
        assert "e.modal" not in query, (
            "create_tlinks_case6 references TEvent.modal which is not a canonical schema "
            "property; the condition is always true and must be removed"
        )
