"""TDD tests for Milestone 0 schema-contract alignment.

These tests intentionally enforce documentation and ontology contract structure:
- canonical / optional / legacy schema tiers must be present in ontology JSON and YAML
- core tier membership must include key maintained labels/relationships
- architecture docs must state ownership split between migration-enforced schema
  and maintained semantic contract docs
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
ONTOLOGY_YAML = ROOT / "textgraphx" / "docs" / "ontology.yaml"
SCHEMA_MD = ROOT / "textgraphx" / "docs" / "schema.md"
ARCH_MD = ROOT / "textgraphx" / "docs" / "architecture-overview.md"


@pytest.mark.unit
class TestSchemaTierContract:
    def _load_json(self) -> dict:
        return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))

    def _load_yaml_text(self) -> str:
        return ONTOLOGY_YAML.read_text(encoding="utf-8")

    def test_json_has_schema_tiers(self):
        payload = self._load_json()
        assert "schema_tiers" in payload

    def test_yaml_has_schema_tiers(self):
        text = self._load_yaml_text()
        assert "schema_tiers:" in text

    def test_schema_tier_keys_match_between_json_and_yaml(self):
        json_tiers = self._load_json()["schema_tiers"]
        text = self._load_yaml_text()
        for key in ["canonical", "optional", "legacy"]:
            assert f"  {key}:" in text
        assert set(json_tiers.keys()) == {"canonical", "optional", "legacy"}

    def test_canonical_core_contains_expected_labels(self):
        tiers = self._load_json()["schema_tiers"]["canonical"]
        labels = set(tiers["node_labels"])
        expected = {
            "AnnotatedText",
            "Sentence",
            "TagOccurrence",
            "NamedEntity",
            "Entity",
            "Frame",
            "FrameArgument",
            "Signal",
            "TIMEX",
            "TEvent",
        }
        assert expected.issubset(labels)
        assert "Keyword" not in labels

    def test_canonical_core_contains_temporal_discourse_relationships(self):
        tiers = self._load_json()["schema_tiers"]["canonical"]
        rels = set(tiers["relationship_types"])
        assert {"TLINK", "CLINK", "SLINK"}.issubset(rels)

    def test_optional_tier_contains_run_markers(self):
        tiers = self._load_json()["schema_tiers"]["optional"]
        labels = set(tiers["node_labels"])
        assert {"PhaseRun", "RefinementRun"}.issubset(labels)

    def test_legacy_tier_contains_relation_abstraction_layer(self):
        tiers = self._load_json()["schema_tiers"]["legacy"]
        labels = set(tiers["node_labels"])
        rels = set(tiers["relationship_types"])
        assert {"Keyword", "Evidence", "Relationship"}.issubset(labels)
        assert {"IS_RELATED_TO", "SOURCE", "DESTINATION", "HAS_EVIDENCE", "FROM", "TO"}.issubset(rels)


@pytest.mark.unit
class TestSchemaContractDocs:
    def test_schema_doc_has_tier_section(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "Canonical, Optional, and Legacy Tiers" in text

    def test_schema_doc_has_governance_sections(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "Canonical Source Hierarchy" in text
        assert "Governance Mode (Balanced)" in text
        assert "Function Authoring Playbook (LPG)" in text
        assert "Schema Drift Control" in text

    def test_architecture_doc_states_schema_ownership_split(self):
        text = ARCH_MD.read_text(encoding="utf-8")
        assert "migrations define the enforced schema" in text
        assert "schema.md defines the maintained semantic contract" in text

    def test_architecture_doc_states_schema_precedence(self):
        text = ARCH_MD.read_text(encoding="utf-8")
        assert "runtime write path -> migration -> schema contract -> ontology metadata" in text

    def test_schema_doc_does_not_claim_fusion_uses_contains(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "now uses `:CONTAINS_SENTENCE`" in text
        assert "still queries `:CONTAINS`" not in text

    def test_schema_doc_does_not_claim_tlinks_reads_modal(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "no longer reads `e.modal`" in text

    def test_schema_doc_tracks_argmtmp_unreachable_branch_resolution(self):
        text = SCHEMA_MD.read_text(encoding="utf-8")
        assert "unreachable `WHEN 'ARGM-TMP'` mapping has been removed" in text


@pytest.mark.unit
class TestGovernanceContract:
    def _load_json(self) -> dict:
        return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))

    def test_ontology_declares_source_hierarchy_precedence(self):
        payload = self._load_json()
        assert "source_hierarchy" in payload
        expected = [
            "runtime_write_paths",
            "applied_migrations",
            "docs_schema_contract",
            "ontology_metadata",
            "architecture_and_historical_docs",
        ]
        assert payload["source_hierarchy"]["precedence"] == expected

    def test_ontology_declares_balanced_governance_mode(self):
        payload = self._load_json()
        assert "governance_mode" in payload
        gov = payload["governance_mode"]
        assert gov["mode"] == "balanced"
        assert "identity_keys" in gov["hard_contract_scope"]
        assert "span_integrity" in gov["hard_contract_scope"]
        assert "enrichment_profile_completeness" in gov["advisory_scope"]
        assert gov["legacy_policy"] == "preserve_with_aliases"

    def test_canonical_tier_contains_mention_layer_nodes_and_edges(self):
        payload = self._load_json()
        canonical = payload["schema_tiers"]["canonical"]
        labels = set(canonical["node_labels"])
        rels = set(canonical["relationship_types"])
        assert {"EntityMention", "EventMention"}.issubset(labels)
        assert {"INSTANTIATES", "HAS_FRAME_ARGUMENT", "EVENT_PARTICIPANT"}.issubset(rels)

    def test_value_is_canonical_when_policy_marks_it_canonical(self):
        payload = self._load_json()
        assert payload["dynamic_label_policy"]["VALUE"]["status"] == "canonical"
        canonical_labels = set(payload["schema_tiers"]["canonical"]["node_labels"])
        assert "VALUE" in canonical_labels


@pytest.mark.unit
class TestReasoningContracts:
    def _load_json(self) -> dict:
        return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))

    def test_relation_endpoint_contract_present(self):
        payload = self._load_json()
        assert "relation_endpoint_contract" in payload

    def test_event_participant_endpoint_contract(self):
        payload = self._load_json()
        ep = payload["relation_endpoint_contract"]["EVENT_PARTICIPANT"]
        assert {"Entity", "NUMERIC", "FrameArgument", "VALUE"}.issubset(set(ep["sources"]))
        assert {"TEvent", "EventMention"}.issubset(set(ep["targets"]))

    def test_temporal_reasoning_profile_present(self):
        payload = self._load_json()
        profile = payload.get("temporal_reasoning_profile", {})
        assert profile
        assert "canonical_reltypes" in profile
        assert "contradiction_pairs" in profile
        assert "closure_rules" in profile

    def test_temporal_reasoning_profile_has_core_reltypes(self):
        profile = self._load_json()["temporal_reasoning_profile"]
        reltypes = set(profile["canonical_reltypes"])
        assert {"BEFORE", "AFTER", "SIMULTANEOUS", "INCLUDES", "IS_INCLUDED", "VAGUE"}.issubset(reltypes)

    def test_event_attribute_vocabulary_present(self):
        payload = self._load_json()
        vocab = payload.get("event_attribute_vocabulary", {})
        assert vocab
        assert "tense" in vocab
        assert "aspect" in vocab
        assert "polarity" in vocab


@pytest.mark.unit
class TestPreflightSpanDiagnostics:
    """Diagnostic entries for missing canonical span fields must exist in the ontology."""

    SPAN_LABELS = ("Frame", "FrameArgument", "NamedEntity", "Antecedent", "CorefMention", "NounChunk", "TIMEX", "TEvent", "Signal")

    def _diagnostics(self) -> list[dict]:
        payload = json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))
        return payload.get("diagnostics", [])

    def _diag_names(self) -> set[str]:
        return {d["name"] for d in self._diagnostics()}

    def test_preflight_span_diagnostics_exist_for_all_canonical_span_labels(self):
        names = self._diag_names()
        missing = [lbl for lbl in self.SPAN_LABELS if f"{lbl}_missing_start_tok" not in names]
        assert not missing, f"missing preflight diagnostics for: {missing}"

    def test_preflight_span_diagnostic_queries_use_null_check(self):
        diags = {d["name"]: d for d in self._diagnostics()}
        for lbl in self.SPAN_LABELS:
            key = f"{lbl}_missing_start_tok"
            assert key in diags, f"missing diagnostic entry {key}"
            query = diags[key].get("query", "")
            assert "start_tok IS NULL" in query, f"{key} query must filter WHERE start_tok IS NULL"

    def test_preflight_span_diagnostic_queries_return_cnt(self):
        diags = {d["name"]: d for d in self._diagnostics()}
        for lbl in self.SPAN_LABELS:
            key = f"{lbl}_missing_start_tok"
            query = diags[key].get("query", "")
            assert "cnt" in query.lower(), f"{key} query must return a 'cnt' alias"
