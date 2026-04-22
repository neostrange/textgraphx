"""TDD tests for Milestone 1 identity and span-contract scaffolding.

These tests validate project artifacts for:
- doc_id normalization policy metadata
- dual coordinate span contract metadata
- migration files required for temporal doc_id cleanup and TIMEX key enforcement
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
ONTOLOGY_YAML = ROOT / "textgraphx" / "docs" / "ontology.yaml"
SCHEMA_MD = ROOT / "textgraphx" / "docs" / "schema.md"
MIGRATIONS = ROOT / "textgraphx" / "schema" / "migrations"


@pytest.mark.unit
class TestMilestone1ContractArtifacts:
    def test_ontology_json_has_identity_policy(self):
        payload = json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))
        assert "identity_policy" in payload
        assert "doc_id_type" in payload["identity_policy"]

    def test_ontology_json_has_span_contract(self):
        payload = json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))
        assert "span_contract" in payload
        contract = payload["span_contract"]
        assert contract.get("token_fields") == ["start_tok", "end_tok"]
        assert contract.get("char_fields") == ["start_char", "end_char"]

    def test_ontology_yaml_has_span_contract_section(self):
        text = ONTOLOGY_YAML.read_text(encoding="utf-8")
        assert "span_contract:" in text
        assert "start_tok" in text
        assert "start_char" in text

    def test_schema_doc_declares_dual_coordinate_contract(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "Span Coordinate Contract" in text
        assert "start_tok" in text
        assert "start_char" in text


@pytest.mark.unit
class TestMilestone1MigrationArtifacts:
    def test_temporal_doc_id_normalization_migration_exists(self):
        mig = MIGRATIONS / "0003_normalize_temporal_doc_id.cypher"
        assert mig.exists(), "expected migration 0003_normalize_temporal_doc_id.cypher"

    def test_timex_natural_key_constraint_migration_exists(self):
        mig = MIGRATIONS / "0004_add_timex_natural_key_constraint.cypher"
        assert mig.exists(), "expected migration 0004_add_timex_natural_key_constraint.cypher"

    def test_doc_id_normalization_migration_targets_timex_and_tevent(self):
        mig = (MIGRATIONS / "0003_normalize_temporal_doc_id.cypher").read_text(encoding="utf-8")
        assert "TIMEX" in mig
        assert "TEvent" in mig
        assert "toInteger" in mig

    def test_timex_constraint_migration_defines_composite_uniqueness(self):
        mig = (MIGRATIONS / "0004_add_timex_natural_key_constraint.cypher").read_text(encoding="utf-8")
        assert "TIMEX" in mig
        assert "tid" in mig
        assert "doc_id" in mig
        assert "CONSTRAINT" in mig


@pytest.mark.unit
class TestMilestone1BackfillMigrationArtifacts:
    """0005 — backfill start_tok/end_tok on all canonical-tier nodes."""

    MIGRATION = MIGRATIONS / "0005_backfill_canonical_span_fields.cypher"

    def test_backfill_migration_exists(self):
        assert self.MIGRATION.exists(), "expected migration 0005_backfill_canonical_span_fields.cypher"

    def test_backfill_migration_targets_all_canonical_labels(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        for label in ("Frame", "FrameArgument", "NamedEntity", "Antecedent", "CorefMention", "NounChunk", "TIMEX", "TEvent"):
            assert label in text, f"migration must target label {label}"

    def test_backfill_migration_guards_with_null_check(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "start_tok IS NULL" in text, "migration must guard updates with WHERE n.start_tok IS NULL"

    def test_backfill_migration_sets_canonical_fields(self):
        text = self.MIGRATION.read_text(encoding="utf-8")
        assert "start_tok" in text
        assert "end_tok" in text

    def test_backfill_migration_preserves_legacy_source_fields(self):
        """The migration must read FROM legacy fields, confirming they are the source."""
        text = self.MIGRATION.read_text(encoding="utf-8")
        # At least one of the known legacy field names must appear as a source
        legacy_sources = ("startIndex", "endIndex", "start_index", "end_index", "begin", "end")
        assert any(src in text for src in legacy_sources), (
            "migration must derive start_tok/end_tok from a known legacy source field"
        )


@pytest.mark.unit
class TestMilestone3MigrationArtifacts:
    """Milestone 3 — constraints and indexes for canonical-tier nodes."""

    MIG_CONSTRAINTS = MIGRATIONS / "0006_add_phaserun_refinementrun_constraints.cypher"
    MIG_INDEXES = MIGRATIONS / "0007_add_canonical_indexes.cypher"

    # --- constraint migration ---

    def test_phaserun_constraint_migration_exists(self):
        assert self.MIG_CONSTRAINTS.exists(), (
            "expected migration 0006_add_phaserun_refinementrun_constraints.cypher"
        )

    def test_phaserun_constraint_migration_covers_phaserun(self):
        text = self.MIG_CONSTRAINTS.read_text(encoding="utf-8")
        assert "PhaseRun" in text, "migration must define a constraint on PhaseRun"
        assert "CONSTRAINT" in text

    def test_phaserun_constraint_migration_covers_refinementrun(self):
        text = self.MIG_CONSTRAINTS.read_text(encoding="utf-8")
        assert "RefinementRun" in text, "migration must define a constraint on RefinementRun"

    def test_phaserun_constraint_migration_is_idempotent(self):
        text = self.MIG_CONSTRAINTS.read_text(encoding="utf-8")
        assert "IF NOT EXISTS" in text, "constraint migration must use IF NOT EXISTS for idempotency"

    # --- index migration ---

    def test_canonical_indexes_migration_exists(self):
        assert self.MIG_INDEXES.exists(), (
            "expected migration 0007_add_canonical_indexes.cypher"
        )

    def test_canonical_indexes_migration_covers_required_labels_and_properties(self):
        text = self.MIG_INDEXES.read_text(encoding="utf-8")
        required = (
            ("FrameArgument", "headTokenIndex"),
            ("NamedEntity", "headTokenIndex"),
            ("TEvent", "doc_id"),
            ("TIMEX", "doc_id"),
        )
        for label, prop in required:
            assert label in text, f"index migration must reference label {label}"
            assert prop in text, f"index migration must reference property {prop}"

    def test_canonical_indexes_migration_is_idempotent(self):
        text = self.MIG_INDEXES.read_text(encoding="utf-8")
        assert "IF NOT EXISTS" in text, "index migration must use IF NOT EXISTS for idempotency"
