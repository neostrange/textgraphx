"""Contract tests for fixtures/refinement_rules/catalog.json.

These tests enforce a strict schema for the refinement rule catalog so the
fixture stays synchronized with RefinementPhase implementation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
CATALOG_PATH = REPO_ROOT / "fixtures" / "refinement_rules" / "catalog.json"
REFINEMENT_PATH = REPO_ROOT / "textgraphx" / "RefinementPhase.py"

REQUIRED_TOP_LEVEL_KEYS = {"catalog_version", "description", "families"}
REQUIRED_FAMILY_KEYS = {"id", "label", "rules"}
REQUIRED_RULE_KEYS = {"method", "provenance_rule_id", "input", "output", "idempotent"}
REQUIRED_FAMILY_IDS = {
    "mention_span_repair",
    "entity_state_annotation",
    "frame_argument_linking",
    "nominal_mention_materialization",
    "nominal_semantic_annotation",
    "canonical_value_materialization",
}


@pytest.fixture(scope="module")
def catalog() -> dict:
    assert CATALOG_PATH.exists(), f"Missing refinement rule catalog: {CATALOG_PATH}"
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def refinement_source() -> str:
    assert REFINEMENT_PATH.exists(), f"Missing RefinementPhase source: {REFINEMENT_PATH}"
    return REFINEMENT_PATH.read_text(encoding="utf-8")


def test_catalog_has_required_top_level_shape(catalog: dict):
    assert isinstance(catalog, dict)
    missing = REQUIRED_TOP_LEVEL_KEYS - set(catalog.keys())
    assert not missing, f"catalog.json missing top-level keys: {sorted(missing)}"

    assert isinstance(catalog["catalog_version"], str) and catalog["catalog_version"].strip()
    assert isinstance(catalog["description"], str) and catalog["description"].strip()
    assert isinstance(catalog["families"], list) and catalog["families"], "families must be a non-empty list"


def test_catalog_family_ids_are_complete_and_unique(catalog: dict):
    families = catalog["families"]
    family_ids = [f.get("id") for f in families]

    assert len(family_ids) == len(set(family_ids)), "family ids must be unique"
    assert set(family_ids) == REQUIRED_FAMILY_IDS, (
        "family ids mismatch; expected exactly "
        f"{sorted(REQUIRED_FAMILY_IDS)}, found {sorted(set(family_ids))}"
    )


def test_each_family_and_rule_has_required_fields(catalog: dict):
    for family in catalog["families"]:
        missing_family = REQUIRED_FAMILY_KEYS - set(family.keys())
        assert not missing_family, (
            f"Family {family.get('id', '<missing-id>')} missing keys: {sorted(missing_family)}"
        )

        assert isinstance(family["id"], str) and family["id"].strip()
        assert isinstance(family["label"], str) and family["label"].strip()
        assert isinstance(family["rules"], list) and family["rules"], (
            f"Family {family['id']} must include at least one rule"
        )

        for rule in family["rules"]:
            missing_rule = REQUIRED_RULE_KEYS - set(rule.keys())
            assert not missing_rule, (
                f"Rule in family {family['id']} missing keys: {sorted(missing_rule)}"
            )

            assert isinstance(rule["method"], str) and rule["method"].strip()
            assert isinstance(rule["provenance_rule_id"], str) and rule["provenance_rule_id"].strip()
            assert isinstance(rule["input"], str) and rule["input"].strip()
            assert isinstance(rule["output"], str) and rule["output"].strip()
            assert isinstance(rule["idempotent"], bool), (
                f"Rule {rule['method']} must set boolean idempotent"
            )


def test_all_catalog_methods_exist_in_refinement_phase(catalog: dict, refinement_source: str):
    implemented_methods = {
        m.group(1)
        for m in re.finditer(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", refinement_source, flags=re.MULTILINE)
    }

    missing_methods = []
    for family in catalog["families"]:
        for rule in family["rules"]:
            method = rule["method"]
            if method not in implemented_methods:
                missing_methods.append(method)

    assert not missing_methods, (
        "Catalog references methods not found in RefinementPhase.py: "
        f"{sorted(set(missing_methods))}"
    )


def test_nominal_family_uid_formula_contract(catalog: dict):
    nominal_family = next(f for f in catalog["families"] if f["id"] == "nominal_mention_materialization")

    by_method = {r["method"]: r for r in nominal_family["rules"]}
    fa = by_method["materialize_nominal_mentions_from_frame_arguments"]
    nc = by_method["materialize_nominal_mentions_from_noun_chunks"]

    assert "uid_formula" in fa and "source='fa'" in fa["uid_formula"]
    assert "uid_formula" in nc and "source='nc'" in nc["uid_formula"]


def test_nominal_family_output_mentions_source_literals(catalog: dict):
    nominal_family = next(f for f in catalog["families"] if f["id"] == "nominal_mention_materialization")

    outputs = {r["method"]: r["output"] for r in nominal_family["rules"]}
    assert "frame_argument_nominal" in outputs["materialize_nominal_mentions_from_frame_arguments"]
    assert "noun_chunk_nominal" in outputs["materialize_nominal_mentions_from_noun_chunks"]
