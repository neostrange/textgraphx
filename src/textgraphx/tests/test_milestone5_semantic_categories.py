"""TDD tests for Milestone 5: Govern Fine-Grained Semantic Categories.

Acceptance criteria:
1. The system can answer non-core role queries without relying on dynamic labels.
2. The allowed values for argumentType are documented and stable.
3. Tests cover expected mappings from ARGM-* to semantic role categories.
4. Policy for NUMERIC and VALUE is explicitly documented and enforced by tests.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_JSON = ROOT / "textgraphx" / "schema" / "ontology.json"
EEP_SRC = ROOT / "textgraphx" / "pipeline" / "phases" / "event_enrichment.py"


def _payload() -> dict:
    return json.loads(ONTOLOGY_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# argumentType vocabulary contract
# ---------------------------------------------------------------------------

# The live mapping in EventEnrichmentPhase.add_non_core_participants_to_event.
# This is the authoritative source we extract from the source file.
EXPECTED_ARGM_MAPPING: dict[str, str] = {
    "ARGM-COM": "Comitative",
    "ARGM-LOC": "Locative",
    "ARGM-DIR": "Directional",
    "ARGM-GOL": "Goal",
    "ARGM-MNR": "Manner",
    "ARGM-EXT": "Extent",
    "ARGM-REC": "Reciprocals",
    "ARGM-PRD": "SecondaryPredication",
    "ARGM-PRP": "PurposeClauses",
    "ARGM-CAU": "CauseClauses",
    "ARGM-DIS": "Discourse",
    "ARGM-MOD": "Modals",
    "ARGM-NEG": "Negation",
    "ARGM-DSP": "DirectSpeech",
    "ARGM-ADV": "Adverbials",
    "ARGM-ADJ": "Adjectival",
    "ARGM-LVB": "LightVerb",
    "ARGM-CXN": "Construction",
}
FALLBACK_CATEGORY = "NonCore"


@pytest.mark.unit
class TestArgumentTypeVocabularyOntology:
    """ontology.json must declare the stable argumentType controlled vocabulary."""

    def test_ontology_has_argument_type_vocabulary_section(self):
        assert "argument_type_vocabulary" in _payload(), (
            "ontology.json must have an 'argument_type_vocabulary' section"
        )

    def test_argument_type_vocabulary_covers_all_argm_types(self):
        vocab = _payload().get("argument_type_vocabulary", {})
        mappings = vocab.get("mappings", {})
        missing = [k for k in EXPECTED_ARGM_MAPPING if k not in mappings]
        assert not missing, f"argument_type_vocabulary.mappings missing entries: {missing}"

    def test_argument_type_vocabulary_values_are_correct(self):
        mappings = _payload()["argument_type_vocabulary"]["mappings"]
        wrong = {k: mappings[k] for k in EXPECTED_ARGM_MAPPING
                 if mappings.get(k) != EXPECTED_ARGM_MAPPING[k]}
        assert not wrong, f"incorrect argumentType mappings: {wrong}"

    def test_argument_type_vocabulary_declares_fallback(self):
        vocab = _payload()["argument_type_vocabulary"]
        assert vocab.get("fallback") == FALLBACK_CATEGORY, (
            f"argument_type_vocabulary.fallback must be '{FALLBACK_CATEGORY}'"
        )

    def test_argument_type_vocabulary_declares_dynamic_labels_policy(self):
        vocab = _payload()["argument_type_vocabulary"]
        assert "dynamic_labels_policy" in vocab, (
            "argument_type_vocabulary must have a 'dynamic_labels_policy' key"
        )


@pytest.mark.unit
class TestArgumentTypeMappingDeterminism:
    """The ARGM-* CASE mapping in EventEnrichmentPhase must match the ontology exactly."""

    def _extract_case_mappings(self) -> dict[str, str]:
        """Parse WHEN 'ARGM-X' THEN 'Category' pairs from the source file."""
        src = EEP_SRC.read_text(encoding="utf-8")
        # Match WHEN 'ARGM-...' THEN '...'
        pattern = re.compile(r"WHEN\s+'(ARGM-[^']+)'\s+THEN\s+'([^']+)'")
        return dict(pattern.findall(src))

    def test_every_expected_argm_type_has_a_case_branch(self):
        found = self._extract_case_mappings()
        missing = [k for k in EXPECTED_ARGM_MAPPING if k not in found]
        assert not missing, (
            f"EventEnrichmentPhase CASE is missing WHEN branches for: {missing}"
        )

    def test_case_branch_values_match_ontology_mappings(self):
        found = self._extract_case_mappings()
        wrong = {k: found[k] for k in EXPECTED_ARGM_MAPPING
                 if found.get(k) != EXPECTED_ARGM_MAPPING[k]}
        assert not wrong, (
            f"EventEnrichmentPhase CASE->category values differ from ontology: {wrong}"
        )

    def test_no_undocumented_argm_branches(self):
        """Every ARGM branch in the source must appear in the ontology vocabulary."""
        found = self._extract_case_mappings()
        ontology_mappings = _payload().get("argument_type_vocabulary", {}).get("mappings", {})
        undocumented = [k for k in found if k not in ontology_mappings]
        assert not undocumented, (
            f"EventEnrichmentPhase has ARGM branches not in ontology vocabulary: {undocumented}"
        )


@pytest.mark.unit
class TestNumericValueLabelPolicy:
    """NUMERIC and VALUE label policy must be documented in ontology.json."""

    def test_ontology_has_dynamic_label_policy_section(self):
        assert "dynamic_label_policy" in _payload(), (
            "ontology.json must have a 'dynamic_label_policy' section"
        )

    def test_numeric_label_policy_is_documented(self):
        policy = _payload().get("dynamic_label_policy", {})
        assert "NUMERIC" in policy, (
            "dynamic_label_policy must document NUMERIC label handling"
        )

    def test_value_label_policy_is_documented(self):
        policy = _payload().get("dynamic_label_policy", {})
        assert "VALUE" in policy, (
            "dynamic_label_policy must document VALUE label handling"
        )

    def test_numeric_policy_declares_status(self):
        entry = _payload()["dynamic_label_policy"].get("NUMERIC", {})
        assert "status" in entry, "NUMERIC policy must have a 'status' key"
        assert entry["status"] in ("transitional", "deprecated"), (
            "NUMERIC policy status must be 'transitional' or 'deprecated'"
        )

    def test_value_policy_declares_status(self):
        entry = _payload()["dynamic_label_policy"].get("VALUE", {})
        assert "status" in entry, "VALUE policy must have a 'status' key"

    def test_numeric_policy_describes_fallback_usage(self):
        entry = _payload()["dynamic_label_policy"].get("NUMERIC", {})
        assert "fallback" in entry.get("description", "").lower(), (
            "NUMERIC policy must describe fallback-only usage"
        )

    def test_value_policy_describes_canonical_query_path(self):
        entry = _payload()["dynamic_label_policy"].get("VALUE", {})
        assert ":VALUE" in entry.get("query_guidance", ""), (
            "VALUE policy must direct read-side queries to canonical VALUE nodes"
        )


@pytest.mark.unit
class TestFrameArgumentDynamicLabelDeprecation:
    """Validate that FrameArgument dynamic label application is deprecated.
    
    These labels (Locative, Directional, etc.) were applied via APOC but never
    used by any query logic. The property-based approach (argumentType) is canonical.
    This test ensures no code tries to filter by these decorative labels.
    """

    def test_add_label_to_non_core_fa_is_noop(self):
        """Verify that add_label_to_non_core_fa() is now a deprecation stub."""
        src = EEP_SRC.read_text(encoding="utf-8")
        
        # The method should NOT contain APOC calls anymore
        assert "apoc.create.addLabels" not in src, (
            "add_label_to_non_core_fa() should not contain APOC label application"
        )
        
        # But the method should still exist for backward compatibility
        assert "def add_label_to_non_core_fa(self):" in src, (
            "add_label_to_non_core_fa() must exist but should be a no-op"
        )
    
    def test_no_cypher_queries_filter_by_frameargument_labels(self):
        """Ensure no Cypher queries filter FrameArgument by dynamic labels."""
        # Search all Python files for FrameArgument label filters
        result = ROOT.glob("textgraphx/**/*.py")
        found_filters = []
        
        for py_file in result:
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8")
            
            # Check for patterns like `:Locative]` or `:Directional]` in FA context
            label_patterns = [
                ":Locative]", ":Directional]", ":Temporal]", ":Manner]", ":Goal]",
                ":Comitative]", ":Extent]", ":Reciprocals]", ":SecondaryPredication]",
                ":PurposeClauses]", ":CauseClauses]", ":Discourse]", ":Modals]",
                ":Negation]", ":DirectSpeech]", ":Adverbials]", ":Adjectival]",
                ":LightVerb]", ":Construction]", ":NonCore]"
            ]
            for pattern in label_patterns:
                if pattern in content:
                    # Filter out false positives: only report if in FrameArgument query context
                    context_lines = content.split("\n")
                    for i, line in enumerate(context_lines):
                        if pattern in line and "FrameArgument" in "".join(context_lines[max(0,i-3):min(len(context_lines),i+3)]):
                            found_filters.append(f"{py_file}:{i+1}: {line.strip()}")
        
        assert not found_filters, (
            f"Found queries filtering FrameArgument by dynamic labels. "
            f"Use argumentType property instead:\n" + "\n".join(found_filters)
        )
    
    def test_schema_md_documents_deprecation(self):
        """Verify that schema.md documents the deprecation."""
        schema_file = ROOT / "textgraphx" / "docs" / "schema.md"
        schema_text = schema_file.read_text(encoding="utf-8")
        
        assert "Dynamic label application deprecated" in schema_text or \
               "add_label_to_non_core_fa" in schema_text, (
            "schema.md should document the deprecation of dynamic label application"
        )
