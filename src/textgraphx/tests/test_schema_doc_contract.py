"""Phase 1 schema-doc contract tests.

Validates that schema.md and ontology.json are consistent on:
1. Deprecated dynamic labels must not appear in the canonical node-label tier.
2. Section 3.1 of schema.md must have a Status column (deprecation signal).
3. The NUMERIC dynamic label must carry 'deprecated' or 'transitional' status in
   the ontology (phase-hardening: will tighten to 'deprecated'-only once stable).
4. The participation edge dual-write inventory is registered in the diagnostics registry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
SCHEMA_MD = ROOT / "textgraphx" / "docs" / "schema.md"


def _ontology() -> dict:
    return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))


def _schema_text() -> str:
    return SCHEMA_MD.read_text(encoding="utf-8")


@pytest.mark.unit
class TestCanonicalTierConsistency:
    """Canonical node-label tier must not list deprecated/transitional dynamic labels."""

    def test_numeric_not_in_canonical_node_labels(self):
        labels = set(
            _ontology()["schema_tiers"]["canonical"]["node_labels"]
        )
        assert "NUMERIC" not in labels, (
            "NUMERIC is a deprecated dynamic label and must not appear in "
            "schema_tiers.canonical.node_labels"
        )

    def test_canonical_tier_contains_value_node(self):
        labels = set(
            _ontology()["schema_tiers"]["canonical"]["node_labels"]
        )
        assert "VALUE" in labels, (
            "VALUE (canonical node type from materialize_canonical_value_nodes) "
            "must remain in schema_tiers.canonical.node_labels"
        )


@pytest.mark.unit
class TestSection31HasStatusColumn:
    """schema.md section 3.1 must have a Status column in its dynamic-label table."""

    def test_section_31_table_has_status_column(self):
        text = _schema_text()
        # Find the section 3.1 block
        assert "### 3.1 Additional labels on `NamedEntity`" in text, (
            "schema.md must have section 3.1"
        )
        # Status column should appear in the table header
        section_start = text.index("### 3.1 Additional labels on `NamedEntity`")
        # Find the next section boundary
        section_end = text.find("\n###", section_start + 1)
        if section_end == -1:
            section_end = len(text)
        section_text = text[section_start:section_end]
        assert "| Status |" in section_text or "| Status" in section_text, (
            "schema.md section 3.1 table must include a 'Status' column "
            "documenting deprecation state for each dynamic label"
        )

    def test_section_31_marks_numeric_as_deprecated(self):
        text = _schema_text()
        section_start = text.index("### 3.1 Additional labels on `NamedEntity`")
        section_end = text.find("\n###", section_start + 1)
        if section_end == -1:
            section_end = len(text)
        section_text = text[section_start:section_end]
        assert "Deprecated" in section_text or "deprecated" in section_text, (
            "schema.md section 3.1 must mark the NUMERIC label as Deprecated"
        )

    def test_section_31_has_deprecation_notice(self):
        text = _schema_text()
        section_start = text.index("### 3.1 Additional labels on `NamedEntity`")
        section_end = text.find("\n###", section_start + 1)
        if section_end == -1:
            section_end = len(text)
        section_text = text[section_start:section_end]
        assert "Deprecation notice" in section_text or "deprecation notice" in section_text, (
            "schema.md section 3.1 must include a deprecation notice block"
        )


@pytest.mark.unit
class TestNumericPolicyStatus:
    """NUMERIC dynamic_label_policy status must reflect its actual write-suppressed state."""

    def test_numeric_policy_status_is_deprecated_or_transitional(self):
        policy = _ontology().get("dynamic_label_policy", {})
        assert "NUMERIC" in policy, "dynamic_label_policy must document NUMERIC"
        status = policy["NUMERIC"].get("status", "")
        assert status in ("deprecated", "transitional"), (
            f"NUMERIC policy status must be 'deprecated' or 'transitional', got '{status}'"
        )

    def test_numeric_policy_has_removal_migration(self):
        policy = _ontology().get("dynamic_label_policy", {})
        entry = policy.get("NUMERIC", {})
        # Either removal_migration field or description mentions migration
        has_removal_ref = (
            "removal_migration" in entry
            or "0019" in entry.get("description", "")
            or "migration" in entry.get("description", "").lower()
        )
        assert has_removal_ref, (
            "NUMERIC policy must reference the removal migration (migration 0019)"
        )


@pytest.mark.unit
class TestParticipationEdgeDiagnosticRegistered:
    """The participation edge migration inventory diagnostic must be registered."""

    def test_participation_edge_diagnostic_is_in_registry(self):
        from textgraphx.evaluation.diagnostics import DIAGNOSTIC_QUERY_REGISTRY
        assert "participation_edge_migration_inventory" in DIAGNOSTIC_QUERY_REGISTRY, (
            "participation_edge_migration_inventory must be registered in "
            "DIAGNOSTIC_QUERY_REGISTRY so quality gate can track IN_FRAME/IN_MENTION coverage"
        )

    def test_participation_edge_query_file_exists(self):
        from textgraphx.queries.query_pack import load_query
        try:
            query = load_query("participation_edge_migration_inventory")
            assert "IN_FRAME" in query or "in_frame_missing" in query, (
                "participation_edge_migration_inventory query must reference IN_FRAME"
            )
            assert "IN_MENTION" in query or "in_mention_missing" in query, (
                "participation_edge_migration_inventory query must reference IN_MENTION"
            )
        except FileNotFoundError:
            pytest.fail(
                "participation_edge_migration_inventory.cypher must exist in queries/"
            )
