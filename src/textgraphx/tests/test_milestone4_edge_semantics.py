"""TDD tests for Milestone 4: Separate Canonical Semantics from Overloaded Predicates.

Phase 4a: Ontology documents new canonical edge types; backfill migration 0008 exists.
Phase 4b: Writers dual-emit both legacy and canonical edge types during the transition window.

New canonical relationship types:
  FRAME_DESCRIBES_EVENT  — Frame -> TEvent (replaces DESCRIBES in this context)
  HAS_FRAME_ARGUMENT     — FrameArgument -> Frame (replaces PARTICIPANT in this context)
  EVENT_PARTICIPANT      — Entity|NUMERIC|FrameArgument -> TEvent (replaces PARTICIPANT here)
"""
from __future__ import annotations

import json
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
MIGRATIONS = ROOT / "textgraphx" / "schema" / "migrations"


@pytest.mark.unit
class TestMilestone4OntologyEdgeTypes:
    """New canonical edges must be documented in ontology.json."""

    NEW_CANONICAL_RELS = ("FRAME_DESCRIBES_EVENT", "HAS_FRAME_ARGUMENT", "EVENT_PARTICIPANT")

    def _payload(self) -> dict:
        return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))

    def test_new_canonical_edges_are_in_relationships_section(self):
        rels = self._payload().get("relationships", {})
        missing = [r for r in self.NEW_CANONICAL_RELS if r not in rels]
        assert not missing, f"ontology.json relationships missing entries: {missing}"

    def test_new_canonical_edges_are_in_canonical_tier(self):
        tier = self._payload()["schema_tiers"]["canonical"]["relationship_types"]
        missing = [r for r in self.NEW_CANONICAL_RELS if r not in tier]
        assert not missing, f"new canonical edges not in schema_tiers.canonical: {missing}"

    def test_ontology_has_deprecated_relationships_section(self):
        payload = self._payload()
        assert "deprecated_relationships" in payload, (
            "ontology.json must have a deprecated_relationships section "
            "marking DESCRIBES and PARTICIPANT as transitioning"
        )

    def test_describes_is_marked_deprecated(self):
        deprecated = self._payload().get("deprecated_relationships", {})
        assert "DESCRIBES" in deprecated, (
            "DESCRIBES must be listed in deprecated_relationships"
        )

    def test_participant_is_marked_deprecated(self):
        deprecated = self._payload().get("deprecated_relationships", {})
        assert "PARTICIPANT" in deprecated, (
            "PARTICIPANT must be listed in deprecated_relationships"
        )

    def test_deprecated_entries_name_canonical_replacements(self):
        deprecated = self._payload().get("deprecated_relationships", {})
        for rel in ("DESCRIBES", "PARTICIPANT"):
            entry = deprecated.get(rel, {})
            assert "replaced_by" in entry, (
                f"deprecated_relationships.{rel} must have a 'replaced_by' key"
            )


@pytest.mark.unit
class TestMilestone4BackfillMigration:
    """Migration 0008 must backfill new canonical edges from legacy ones."""

    MIGRATION = MIGRATIONS / "0008_backfill_canonical_event_edges.cypher"

    def test_migration_exists(self):
        assert self.MIGRATION.exists(), (
            "expected migration 0008_backfill_canonical_event_edges.cypher"
        )

    def test_migration_creates_frame_describes_event_edges(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "FRAME_DESCRIBES_EVENT" in text, (
            "migration must create FRAME_DESCRIBES_EVENT edges"
        )

    def test_migration_creates_has_frame_argument_edges(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "HAS_FRAME_ARGUMENT" in text, (
            "migration must create HAS_FRAME_ARGUMENT edges"
        )

    def test_migration_creates_event_participant_edges(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "EVENT_PARTICIPANT" in text, (
            "migration must create EVENT_PARTICIPANT edges"
        )

    def test_migration_sources_from_legacy_describes(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "DESCRIBES" in text, (
            "migration must traverse existing :DESCRIBES edges as the source"
        )

    def test_migration_sources_from_legacy_participant(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "PARTICIPANT" in text, (
            "migration must traverse existing :PARTICIPANT edges as the source"
        )

    def test_migration_is_idempotent(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "MERGE" in text, (
            "migration must use MERGE for idempotent edge creation"
        )


# ---------------------------------------------------------------------------
# Phase 4b helpers
# ---------------------------------------------------------------------------

def _all_run_queries(mock_graph) -> list[str]:
    """Return all Cypher strings passed to graph.run() as the first positional arg."""
    queries = []
    for c in mock_graph.run.call_args_list:
        args = c[0]
        if args:
            queries.append(args[0])
    return queries


def _load_srl_class():
    """Load SRLProcessor without connecting to Neo4j or importing spaCy."""
    for mod_name in (
        "spacy", "spacy.tokens", "spacy.matcher", "spacy.language",
    ):
        if mod_name not in sys.modules:
            m = types.ModuleType(mod_name)
            sys.modules[mod_name] = m
    sys.modules["spacy"].Language = MagicMock()
    sys.modules["spacy"].load = MagicMock(return_value=MagicMock())
    sys.modules["spacy.tokens"].Doc = MagicMock()
    sys.modules["spacy.tokens"].Token = MagicMock()
    sys.modules["spacy.tokens"].Span = MagicMock()
    sys.modules["spacy.matcher"].Matcher = MagicMock()
    sys.modules["spacy.matcher"].DependencyMatcher = MagicMock()
    sys.modules["spacy.language"].Language = MagicMock()

    with patch("textgraphx.neo4j_client.make_graph_from_config", return_value=MagicMock()):
        from textgraphx.text_processing_components.SRLProcessor import SRLProcessor
    return SRLProcessor


# ---------------------------------------------------------------------------
# Phase 4b: EventEnrichmentPhase writer dual-emit
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEventEnrichmentWriterDualEmit:
    """EventEnrichmentPhase writers must emit both legacy and canonical edge types."""

    EEP_SRC = ROOT / "textgraphx" / "EventEnrichmentPhase.py"

    def _src(self) -> str:
        return self.EEP_SRC.read_text(encoding="utf-8")

    def _method_body(self, method_name: str) -> str:
        src = self._src()
        start = src.index(f"def {method_name}(")
        tail = src[start:]
        nxt = re.search(r"\n    def |\nclass ", tail[len(method_name):])
        return tail[: len(method_name) + nxt.start()] if nxt else tail

    def test_link_frame_to_event_emits_frame_describes_event(self):
        body = self._method_body("link_frameArgument_to_event")
        assert "FRAME_DESCRIBES_EVENT" in body, (
            "link_frameArgument_to_event must emit FRAME_DESCRIBES_EVENT alongside DESCRIBES"
        )

    def test_link_frame_to_event_preserves_legacy_describes(self):
        body = self._method_body("link_frameArgument_to_event")
        assert "DESCRIBES" in body, (
            "link_frameArgument_to_event must still emit legacy :DESCRIBES during transition"
        )

    def test_add_core_participants_emits_event_participant(self):
        body = self._method_body("add_core_participants_to_event")
        assert "EVENT_PARTICIPANT" in body, (
            "add_core_participants_to_event must emit EVENT_PARTICIPANT alongside PARTICIPANT"
        )

    def test_add_core_participants_preserves_legacy_participant(self):
        body = self._method_body("add_core_participants_to_event")
        assert "PARTICIPANT" in body, (
            "add_core_participants_to_event must still emit legacy :PARTICIPANT during transition"
        )

    def test_add_non_core_participants_emits_event_participant(self):
        body = self._method_body("add_non_core_participants_to_event")
        assert "EVENT_PARTICIPANT" in body, (
            "add_non_core_participants_to_event must emit EVENT_PARTICIPANT alongside PARTICIPANT"
        )

    def test_add_non_core_participants_preserves_legacy_participant(self):
        body = self._method_body("add_non_core_participants_to_event")
        assert "PARTICIPANT" in body, (
            "add_non_core_participants_to_event must still emit legacy :PARTICIPANT during transition"
        )

    def test_core_participant_edges_include_provenance_fields(self):
        body = self._method_body("add_core_participants_to_event")
        assert "r.confidence = 0.65" in body
        assert "r.evidence_source = 'event_enrichment'" in body
        assert "r.rule_id = 'participant_linking_core'" in body
        assert "nr.confidence = 0.65" in body
        assert "nr.evidence_source = 'event_enrichment'" in body
        assert "nr.rule_id = 'participant_linking_core'" in body

    def test_non_core_participant_edges_include_provenance_fields(self):
        body = self._method_body("add_non_core_participants_to_event")
        assert "r.confidence = 0.60" in body
        assert "r.evidence_source = 'event_enrichment'" in body
        assert "r.rule_id = 'participant_linking_non_core'" in body
        assert "nr.confidence = 0.60" in body
        assert "nr.evidence_source = 'event_enrichment'" in body
        assert "nr.rule_id = 'participant_linking_non_core'" in body


# ---------------------------------------------------------------------------
# Phase 4b: SRLProcessor writer dual-emit
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSRLProcessorWriterDualEmit:
    """SRLProcessor must emit HAS_FRAME_ARGUMENT alongside PARTICIPANT when linking
    FrameArgument to Frame."""

    SRL_SRC = ROOT / "textgraphx" / "text_processing_components" / "SRLProcessor.py"

    def _src(self) -> str:
        return self.SRL_SRC.read_text(encoding="utf-8")

    def test_frame_argument_linking_emits_has_frame_argument(self):
        src = self._src()
        assert "HAS_FRAME_ARGUMENT" in src, (
            "SRLProcessor must emit :HAS_FRAME_ARGUMENT when linking FrameArgument to Frame"
        )

    def test_frame_argument_linking_preserves_legacy_participant(self):
        src = self._src()
        assert "PARTICIPANT" in src, (
            "SRLProcessor must still emit legacy :PARTICIPANT during transition"
        )


# ---------------------------------------------------------------------------
# Phase 4b: TlinksRecognizer reader dual-aware matching
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTlinksRecognizerReaderDualAware:
    """TlinksRecognizer should read canonical event description edges with legacy fallback."""

    TLINKS_SRC = ROOT / "textgraphx" / "TlinksRecognizer.py"

    def _src(self) -> str:
        return self.TLINKS_SRC.read_text(encoding="utf-8")

    def test_tlinks_queries_include_canonical_frame_describes_event(self):
        src = self._src()
        assert "FRAME_DESCRIBES_EVENT" in src, (
            "TlinksRecognizer queries must match :FRAME_DESCRIBES_EVENT during transition"
        )

    def test_tlinks_queries_preserve_legacy_describes_fallback(self):
        src = self._src()
        assert "DESCRIBES" in src, (
            "TlinksRecognizer queries must retain legacy :DESCRIBES fallback during transition"
        )

    def test_tlinks_queries_include_canonical_has_frame_argument(self):
        src = self._src()
        assert "HAS_FRAME_ARGUMENT" in src, (
            "TlinksRecognizer queries must match :HAS_FRAME_ARGUMENT during transition"
        )

    def test_tlinks_queries_preserve_legacy_participant_fallback(self):
        src = self._src()
        assert "PARTICIPANT" in src, (
            "TlinksRecognizer queries must retain legacy :PARTICIPANT fallback during transition"
        )

    def test_tlinks_queries_include_canonical_has_frame_argument(self):
        src = self._src()
        assert "HAS_FRAME_ARGUMENT" in src, (
            "TlinksRecognizer queries must match :HAS_FRAME_ARGUMENT during transition"
        )

    def test_tlinks_queries_preserve_legacy_participant_fallback(self):
        src = self._src()
        assert "PARTICIPANT" in src, (
            "TlinksRecognizer queries must retain legacy :PARTICIPANT fallback during transition"
        )
