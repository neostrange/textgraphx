"""Contract tests for entity-extraction id helpers.

Validates hard invariants of make_entity_id, make_nounchunk_id, and the
general ID-determinism guarantee defined in §5.1 of copilot-instructions.md.

All tests are pure-Python (no DB, no I/O).
"""
import pytest
from textgraphx.utils.id_utils import (
    make_entity_id,
    make_ne_id,
    make_nounchunk_id,
)


# ---------------------------------------------------------------------------
# make_entity_id
# ---------------------------------------------------------------------------

class TestMakeEntityId:
    """make_entity_id contract tests."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_kb_id_produces_cross_doc_stable_id(self):
        """Two docs with the same kb_id must yield the same Entity id."""
        id_doc1 = make_entity_id("doc1", "http://dbpedia.org/resource/France", "GPE")
        id_doc2 = make_entity_id("doc99", "http://dbpedia.org/resource/France", "GPE")
        assert id_doc1 == id_doc2, "kb_id-based ids must be cross-doc stable"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_unresolved_entity_is_cross_doc_stable(self):
        """Same surface and type across different docs MUST share an Entity id.

        Unresolved (non-URI) entities with the same normalized surface form
        and NE type represent the same real-world referent and must merge to
        a single canonical node across documents.
        """
        id_doc1 = make_entity_id("doc1", "France", "GPE")
        id_doc2 = make_entity_id("doc2", "France", "GPE")
        assert id_doc1 == id_doc2, "Unresolved entity ids must be cross-document stable"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_same_doc_same_surface_same_type_is_stable(self):
        """Repeated calls with identical inputs must produce identical output."""
        a = make_entity_id("doc1", "France", "GPE")
        b = make_entity_id("doc1", "France", "GPE")
        assert a == b

    @pytest.mark.unit
    @pytest.mark.contract
    def test_normalization_folds_casing(self):
        """Surface text differing only in case must yield the same id."""
        a = make_entity_id("doc1", "france", "GPE")
        b = make_entity_id("doc1", "FRANCE", "GPE")
        assert a == b, "make_entity_id must normalize surface text casing"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_normalization_folds_whitespace(self):
        """Extra whitespace must not produce a different id."""
        a = make_entity_id("doc1", "New  York", "GPE")
        b = make_entity_id("doc1", "New York", "GPE")
        assert a == b, "make_entity_id must normalize internal whitespace"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_different_types_produce_different_ids(self):
        """Same doc + same surface but different NE types must differ."""
        person_id = make_entity_id("doc1", "Jordan", "PERSON")
        gpe_id = make_entity_id("doc1", "Jordan", "GPE")
        assert person_id != gpe_id

    @pytest.mark.unit
    @pytest.mark.contract
    def test_none_surface_is_handled(self):
        """None surface must not raise — returns a stable id."""
        result = make_entity_id("doc1", None, "GPE")
        assert isinstance(result, str) and len(result) > 0

    @pytest.mark.unit
    @pytest.mark.contract
    def test_id_starts_with_entity_prefix(self):
        """All entity ids must share the 'entity_' prefix for namespace clarity."""
        assert make_entity_id("doc1", "France", "GPE").startswith("entity_")
        assert make_entity_id("doc1", "http://dbpedia.org/resource/France", "GPE").startswith("entity_")

    @pytest.mark.unit
    @pytest.mark.contract
    def test_uri_with_colon_scheme_also_cross_doc(self):
        """URI-like surfaces using colon-scheme notation are also cross-doc stable."""
        id1 = make_entity_id("docA", "wd:Q142", "GPE")
        id2 = make_entity_id("docB", "wd:Q142", "GPE")
        assert id1 == id2


# ---------------------------------------------------------------------------
# make_nounchunk_id
# ---------------------------------------------------------------------------

class TestMakeNounChunkId:
    """make_nounchunk_id contract tests."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_same_start_different_end_produces_different_ids(self):
        """Two chunks starting at the same token but differing in end must not collide."""
        id_a = make_nounchunk_id("doc1", 3, end=5, head_tok=4)
        id_b = make_nounchunk_id("doc1", 3, end=7, head_tok=4)
        assert id_a != id_b, "NounChunk ids must include end_tok to prevent collisions"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_same_span_different_doc_produces_different_ids(self):
        """Identical spans in different documents must not share an id."""
        id_a = make_nounchunk_id("doc1", 3, end=5, head_tok=4)
        id_b = make_nounchunk_id("doc2", 3, end=5, head_tok=4)
        assert id_a != id_b

    @pytest.mark.unit
    @pytest.mark.contract
    def test_deterministic_on_repeated_calls(self):
        """Repeated identical calls must produce the same id."""
        a = make_nounchunk_id("doc1", 3, end=5, head_tok=4)
        b = make_nounchunk_id("doc1", 3, end=5, head_tok=4)
        assert a == b

    @pytest.mark.unit
    @pytest.mark.contract
    def test_id_has_nc_prefix(self):
        """NounChunk ids must carry the 'nc_' namespace prefix."""
        nc_id = make_nounchunk_id("doc1", 0, end=2, head_tok=1)
        assert nc_id.startswith("nc_"), f"Expected 'nc_' prefix, got: {nc_id}"


# ---------------------------------------------------------------------------
# make_ne_id — existing helper, regression guard
# ---------------------------------------------------------------------------

class TestMakeNeId:
    """Regression guard for the existing make_ne_id helper."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ne_id_is_deterministic(self):
        ne_id_a = make_ne_id("doc1", 0, 3, "PERSON")
        ne_id_b = make_ne_id("doc1", 0, 3, "PERSON")
        assert ne_id_a == ne_id_b

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ne_id_encodes_type(self):
        person = make_ne_id("doc1", 0, 3, "PERSON")
        org = make_ne_id("doc1", 0, 3, "ORG")
        assert person != org, "make_ne_id must differentiate by NE type"
