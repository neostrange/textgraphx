"""TDD tests for Milestone 6: Rationalize the Legacy Relation-Abstraction Layer.

Decision: Option B — deprecate.

Rationale derived from codebase audit:
- Evidence and Relationship are already in schema_tiers.legacy in ontology.json.
- The only writer is TextProcessor.build_relationships_inferred_graph, which uses
  non-deterministic id(r) as the node identity (unstable across restarts).
- No maintained read-side consumers exist for this layer.
- The layer is named in the legacy tier and its edge types (IS_RELATED_TO, SOURCE,
  DESTINATION, HAS_EVIDENCE, FROM, TO) are already separated from canonical.

Acceptance criteria:
1. The project no longer treats this layer ambiguously.
2. Maintainers know not to invest in it (deprecated, not removed).
3. The ontology explicitly records the decision and deprecation rationale.
4. The unstable id(r) identity issue is documented.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
TEXT_PROCESSOR_SRC = ROOT / "textgraphx" / "pipeline/phases/text_processor.py"


def _payload() -> dict:
    return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))


@pytest.mark.unit
class TestM6RelationLayerPolicyDecision:
    """The ontology must record an explicit policy decision for the legacy relation layer."""

    def test_ontology_has_legacy_layer_policy_section(self):
        assert "legacy_layer_policy" in _payload(), (
            "ontology.json must have a 'legacy_layer_policy' section for Milestone 6"
        )

    def test_legacy_layer_policy_covers_evidence(self):
        policy = _payload().get("legacy_layer_policy", {})
        assert "Evidence" in policy, (
            "legacy_layer_policy must document the Evidence node label"
        )

    def test_legacy_layer_policy_covers_relationship(self):
        policy = _payload().get("legacy_layer_policy", {})
        assert "Relationship" in policy, (
            "legacy_layer_policy must document the Relationship node label"
        )

    def test_evidence_policy_is_deprecated(self):
        entry = _payload()["legacy_layer_policy"].get("Evidence", {})
        assert entry.get("status") == "deprecated", (
            "Evidence must be marked status=deprecated"
        )

    def test_relationship_policy_is_deprecated(self):
        entry = _payload()["legacy_layer_policy"].get("Relationship", {})
        assert entry.get("status") == "deprecated", (
            "Relationship must be marked status=deprecated"
        )

    def test_evidence_policy_documents_identity_issue(self):
        entry = _payload()["legacy_layer_policy"].get("Evidence", {})
        notes = entry.get("notes", "")
        assert "id(r)" in notes or "non-deterministic" in notes, (
            "Evidence policy notes must mention the id(r) non-deterministic identity problem"
        )

    def test_legacy_layer_policy_names_deprecation_path(self):
        policy = _payload().get("legacy_layer_policy", {})
        # At least one entry must state a deprecation path
        has_path = any(
            "deprecation_path" in v
            for v in policy.values()
            if isinstance(v, dict)
        )
        assert has_path, (
            "legacy_layer_policy must include a 'deprecation_path' key in at least one entry"
        )


@pytest.mark.unit
class TestM6EvidenceLayerInLegacyTier:
    """Confirm Evidence and Relationship labels remain in the legacy schema tier
    (not promoted to canonical) — this should already be true and must stay true."""

    def test_evidence_not_in_canonical_tier(self):
        canonical = _payload()["schema_tiers"]["canonical"]["node_labels"]
        assert "Evidence" not in canonical, (
            "Evidence must NOT be in the canonical schema tier"
        )

    def test_relationship_not_in_canonical_tier(self):
        canonical = _payload()["schema_tiers"]["canonical"]["node_labels"]
        assert "Relationship" not in canonical, (
            "Relationship must NOT be in the canonical schema tier"
        )

    def test_evidence_in_legacy_tier(self):
        legacy = _payload()["schema_tiers"]["legacy"]["node_labels"]
        assert "Evidence" in legacy, (
            "Evidence must remain in schema_tiers.legacy"
        )

    def test_relationship_in_legacy_tier(self):
        legacy = _payload()["schema_tiers"]["legacy"]["node_labels"]
        assert "Relationship" in legacy, (
            "Relationship must remain in schema_tiers.legacy"
        )
