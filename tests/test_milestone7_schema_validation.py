"""TDD tests for Milestone 7: Schema-Level Validation and Regression Coverage.

Acceptance criteria (from schema-evolution-plan.md §Milestone 7):
1. CI fails when canonical edge names or key properties drift unintentionally.
2. CI fails when required constraints are missing.
3. CI can validate a migrated graph and a freshly initialized graph.

Test categories:
  TestSchemaInvariants  — locks canonical labels, rels, and key properties in place.
  TestMigrationManifest — verifies ontology records an authoritative migration manifest.
  TestMigrationFiles    — verifies migration .cypher files are present and plausible.
  TestNegativeDriftDetection — negative tests proving schema drift is caught early.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
MIGRATIONS_DIR = ROOT / "textgraphx" / "schema" / "migrations"
TEXT_PROCESSOR_SRC = ROOT / "textgraphx" / "TextProcessor.py"


def _payload() -> dict:
    return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Category 1 – Schema invariants (lock names and properties against drift)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSchemaInvariants:
    """Every canonical relationship type must have a documented description.
    Every identity-critical node must document its key properties.
    Dynamic-policy labels with status=canonical must appear in the canonical tier."""

    def test_all_canonical_rels_have_entries_in_relationships_dict(self):
        """Each rel type in canonical tier must have an entry in the top-level
        'relationships' dict so maintainers know what it means."""
        payload = _payload()
        canonical_rels = set(payload["schema_tiers"]["canonical"]["relationship_types"])
        documented = set(payload.get("relationships", {}).keys())
        undocumented = canonical_rels - documented
        assert not undocumented, (
            f"Canonical relationship types missing from 'relationships' dict: {sorted(undocumented)}"
        )

    def test_timex_has_tid_and_doc_id_in_key_properties(self):
        props = _payload()["nodes"]["TIMEX"]["key_properties"]
        assert "tid" in props and "doc_id" in props, (
            "TIMEX must list both 'tid' and 'doc_id' in key_properties (composite natural key)"
        )

    def test_tevent_has_eiid_and_doc_id_in_key_properties(self):
        props = _payload()["nodes"]["TEvent"]["key_properties"]
        assert "eiid" in props and "doc_id" in props, (
            "TEvent must list both 'eiid' and 'doc_id' in key_properties (composite natural key)"
        )

    def test_identity_policy_doc_id_type_is_integer(self):
        assert _payload()["identity_policy"]["doc_id_type"] == "integer", (
            "identity_policy.doc_id_type must be 'integer' — changing this would break M1 guarantees"
        )

    def test_deprecated_rels_each_name_a_replacement(self):
        deprecated = _payload().get("deprecated_relationships", {})
        for rel_name, entry in deprecated.items():
            replacements = entry.get("replaced_by", [])
            assert replacements, (
                f"Deprecated relationship '{rel_name}' must name at least one replacement in 'replaced_by'"
            )

    def test_numeric_label_in_canonical_tier(self):
        """dynamic_label_policy marks NUMERIC as 'canonical'; it must appear in
        schema_tiers.canonical.node_labels so queriers can treat it as a first-class label."""
        policy_status = _payload()["dynamic_label_policy"]["NUMERIC"]["status"]
        assert policy_status == "canonical"  # policy itself is pre-existing, should pass
        canonical_labels = _payload()["schema_tiers"]["canonical"]["node_labels"]
        assert "NUMERIC" in canonical_labels, (
            "NUMERIC has dynamic_label_policy.status='canonical' but is absent from "
            "schema_tiers.canonical.node_labels — this is a documentation inconsistency"
        )

    def test_argument_type_vocabulary_has_all_argm_codes(self):
        expected = {
            "ARGM-COM", "ARGM-LOC", "ARGM-DIR", "ARGM-GOL", "ARGM-MNR",
            "ARGM-EXT", "ARGM-REC", "ARGM-PRD", "ARGM-PRP", "ARGM-CAU",
            "ARGM-DIS", "ARGM-MOD", "ARGM-NEG", "ARGM-DSP", "ARGM-ADV",
            "ARGM-ADJ", "ARGM-LVB", "ARGM-CXN",
        }
        mappings = set(_payload()["argument_type_vocabulary"]["mappings"].keys())
        missing = expected - mappings
        assert not missing, f"argument_type_vocabulary missing ARGM codes: {sorted(missing)}"

    def test_has_lemma_is_canonical_and_refers_to_no_longer_covers_tag_edges(self):
        payload = _payload()
        canonical_rels = set(payload["schema_tiers"]["canonical"]["relationship_types"])
        assert "HAS_LEMMA" in canonical_rels, (
            "HAS_LEMMA must be listed in schema_tiers.canonical.relationship_types"
        )

        refers_pairs = {
            tuple(pair)
            for pair in payload["relation_endpoint_contract"]["REFERS_TO"]["allowed_pairs"]
        }
        has_lemma_pairs = {
            tuple(pair)
            for pair in payload["relation_endpoint_contract"]["HAS_LEMMA"]["allowed_pairs"]
        }
        assert ("TagOccurrence", "Tag") not in refers_pairs, (
            "TagOccurrence->Tag must not remain in REFERS_TO endpoint contract"
        )
        assert ("TagOccurrence", "Tag") in has_lemma_pairs, (
            "TagOccurrence->Tag must be governed by HAS_LEMMA endpoint contract"
        )

    def test_span_aliases_do_not_overlap_token_and_char_spaces(self):
        aliases = _payload()["span_contract"]["legacy_aliases"]
        token_aliases = set(aliases.get("start_tok", [])) | set(aliases.get("end_tok", []))
        char_aliases = set(aliases.get("start_char", [])) | set(aliases.get("end_char", []))
        overlap = token_aliases & char_aliases
        assert not overlap, (
            "span_contract.legacy_aliases must keep token and character aliases disjoint; "
            f"overlap found: {sorted(overlap)}"
        )


# ---------------------------------------------------------------------------
# Category 2 – Migration manifest (lock the migration sequence in ontology)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMigrationManifest:
    """The ontology must record an authoritative ordered list of expected migration files
    so CI can verify the on-disk sequence against the schema contract."""

    def test_ontology_has_migration_manifest_section(self):
        assert "migration_manifest" in _payload(), (
            "ontology.json must have a 'migration_manifest' section listing expected migration files"
        )

    def test_migration_manifest_covers_all_eight_files(self):
        manifest = _payload().get("migration_manifest", {})
        files = manifest.get("files", [])
        assert len(files) == 16, (
            f"migration_manifest.files must list exactly 16 migration files; found {len(files)}"
        )

    def test_migration_manifest_files_are_ordered(self):
        files = _payload().get("migration_manifest", {}).get("files", [])
        prefixes = [f.split("_")[0] for f in files if isinstance(f, str)]
        assert prefixes == sorted(prefixes), (
            "migration_manifest.files must be listed in ascending numeric order"
        )

    def test_migration_manifest_starts_at_0001(self):
        files = _payload().get("migration_manifest", {}).get("files", [])
        assert files and files[0].startswith("0001"), (
            "migration_manifest.files must start with the 0001 constraint migration"
        )

    def test_migration_manifest_ends_at_0008(self):
        files = _payload().get("migration_manifest", {}).get("files", [])
        assert files and files[-1].startswith("0016"), (
            "migration_manifest.files must end with the 0016 value node formalization migration"
        )


# ---------------------------------------------------------------------------
# Category 3 – Migration file presence and plausibility
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMigrationFiles:
    """All expected .cypher migration files must exist and have plausible content."""

    def _files(self) -> list[Path]:
        return sorted(MIGRATIONS_DIR.glob("*.cypher"))

    def test_eight_migration_files_exist(self):
        files = self._files()
        assert len(files) == 16, (
            f"Expected 16 .cypher migration files; found {len(files)}: {[f.name for f in files]}"
        )

    def test_migration_files_are_non_empty(self):
        for f in self._files():
            assert f.read_text(encoding="utf-8").strip(), f"{f.name} is empty"

    def test_no_gap_in_migration_sequence(self):
        files = self._files()
        numbers = [int(f.name[:4]) for f in files]
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        assert numbers == expected, (
            f"Gap detected in migration sequence. Expected {expected}, got {numbers}"
        )

    def test_constraint_migrations_contain_create_constraint(self):
        constraint_files = [
            "0001_create_constraints.cypher",
            "0002_create_namedentity_tokenid_constraint.cypher",
            "0004_add_timex_natural_key_constraint.cypher",
            "0006_add_phaserun_refinementrun_constraints.cypher",
        ]
        for name in constraint_files:
            content = (MIGRATIONS_DIR / name).read_text(encoding="utf-8").upper()
            assert "CREATE CONSTRAINT" in content, (
                f"{name} must contain 'CREATE CONSTRAINT'"
            )

    def test_index_migration_contains_create_index(self):
        content = (MIGRATIONS_DIR / "0007_add_canonical_indexes.cypher").read_text(encoding="utf-8").upper()
        assert "CREATE INDEX" in content, (
            "0007_add_canonical_indexes.cypher must contain 'CREATE INDEX'"
        )

    def test_backfill_migrations_contain_merge(self):
        for name in [
            "0003_normalize_temporal_doc_id.cypher",
            "0005_backfill_canonical_span_fields.cypher",
            "0008_backfill_canonical_event_edges.cypher",
        ]:
            content = (MIGRATIONS_DIR / name).read_text(encoding="utf-8").upper()
            assert "MERGE" in content or "SET" in content, (
                f"{name} must contain MERGE or SET (backfill operation)"
            )


# ---------------------------------------------------------------------------
# Category 4 – Negative drift-detection tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestNegativeDriftDetection:
    """These tests fail when schema invariants are violated — they guard against
    accidental drift: promoting legacy labels, losing deprecation docs, etc."""

    def test_evidence_not_promoted_to_canonical(self):
        canonical = _payload()["schema_tiers"]["canonical"]["node_labels"]
        assert "Evidence" not in canonical, (
            "DRIFT DETECTED: Evidence must never be in the canonical tier"
        )

    def test_relationship_not_promoted_to_canonical(self):
        canonical = _payload()["schema_tiers"]["canonical"]["node_labels"]
        assert "Relationship" not in canonical, (
            "DRIFT DETECTED: Relationship must never be in the canonical tier"
        )

    def test_legacy_rel_types_not_in_canonical_tier(self):
        legacy_rels = set(_payload()["schema_tiers"]["legacy"]["relationship_types"])
        canonical_rels = set(_payload()["schema_tiers"]["canonical"]["relationship_types"])
        overlap = legacy_rels & canonical_rels
        assert not overlap, (
            f"DRIFT DETECTED: relationship types appear in both canonical and legacy tiers: {overlap}"
        )

    def test_id_r_as_node_key_isolated_to_legacy_writer(self):
        """The anti-pattern {id: id(r)} (using a Neo4j internal relationship ID as a
        node property key, making identity non-deterministic across restarts) must only
        appear in TextProcessor.py — the one legacy writer we documented in M6.
        Read-only RETURN id(r) clauses are acceptable and excluded from this check."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "id(r)", "--include=*.py",
             str(ROOT / "textgraphx")],
            capture_output=True, text=True
        )
        hits = []
        for line in result.stdout.splitlines():
            if "TextProcessor.py" in line:
                continue
            if line.strip().startswith("#"):
                continue
            # Only flag write patterns: where id(r) is assigned as a node property value
            # e.g. {id: id(r) or id:id(r)  — not plain RETURN id(r)
            code = line.split(":", 2)[-1] if line.count(":") >= 2 else line
            if re.search(r"id\s*:\s*id\(r\)", code):
                hits.append(line)
        assert not hits, (
            "DRIFT DETECTED: id(r) used as a node property key outside TextProcessor.py. "
            "New code must use stable deterministic ids:\n" + "\n".join(hits)
        )

    def test_deprecated_rels_still_have_deprecation_records(self):
        """Guard against someone silently removing the deprecated_relationships section."""
        deprecated = _payload().get("deprecated_relationships", {})
        for name in ("DESCRIBES", "PARTICIPANT"):
            assert name in deprecated, (
                f"DRIFT DETECTED: '{name}' must remain in deprecated_relationships during "
                f"the dual-write transition period"
            )

    def test_span_contract_canonical_fields_unchanged(self):
        """Guard the M1 span contract: token fields must stay start_tok/end_tok."""
        token_fields = _payload()["span_contract"]["token_fields"]
        assert "start_tok" in token_fields and "end_tok" in token_fields, (
            "DRIFT DETECTED: span_contract.token_fields must include start_tok and end_tok"
        )
