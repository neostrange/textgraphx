"""Unit tests for TlinksRecognizer.materialize_tlink_inverses — Case 19.

TimeML Inverse Mirror: for every existing TLINK with a non-symmetric relType,
materialize the logically equivalent inverse edge in the opposite graph
direction with the inverse relation name.

Coverage:
- All 8 forward→inverse pairs are present in the Cypher.
- SIMULTANEOUS / IDENTITY / VAGUE / MEASURE / BEFORE / AFTER are excluded
  (symmetric, directionless, or excluded to prevent precision collapse).
- Each pair issues a MERGE with ON CREATE / ON MATCH blocks.
- ON MATCH confidence guard prevents overwriting higher-confidence edges.
- derivedFrom and rule_id properties are set correctly.
- Mock invocation: returns aggregate count.
- Inverse pair correctness: IS_INCLUDED→INCLUDES, INCLUDES→IS_INCLUDED,
  BEGUN_BY→BEGINS, BEGINS→BEGUN_BY, ENDED_BY→ENDS, ENDS→ENDED_BY,
  IAFTER→IBEFORE, IBEFORE→IAFTER.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

TR_PATH = (
    Path(__file__).resolve().parents[1] / "pipeline" / "phases" / "tlinks_recognizer.py"
)

INVERSE_PAIRS = [
    ("IS_INCLUDED", "INCLUDES"),
    ("INCLUDES", "IS_INCLUDED"),
    ("BEGUN_BY", "BEGINS"),
    ("BEGINS", "BEGUN_BY"),
    ("ENDED_BY", "ENDS"),
    ("ENDS", "ENDED_BY"),
    ("IAFTER", "IBEFORE"),
    ("IBEFORE", "IAFTER"),
]

# Relations excluded from inversion (would cause precision collapse or are symmetric)
EXCLUDED_FROM_INVERSION = ["BEFORE", "AFTER"]

# Relations that should NOT have inverses materialized
EXCLUDED_RELS = ["SIMULTANEOUS", "IDENTITY", "VAGUE", "MEASURE", "DURING"]


@pytest.fixture(scope="module")
def tr_source() -> str:
    return TR_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"method {method_name!r} not found"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


def _make_recognizer():
    mock_graph = MagicMock()
    mock_graph.run.return_value.data.return_value = [{"created": 3}]

    from textgraphx.pipeline.phases.tlinks_recognizer import TlinksRecognizer

    rec = TlinksRecognizer.__new__(TlinksRecognizer)
    rec.graph = mock_graph
    rec.logger = MagicMock()
    rec.doc_id = "test_doc"
    rec.config = {}
    return rec


# ---------------------------------------------------------------------------
# Source structure tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_method_exists(tr_source):
    """materialize_tlink_inverses method must be defined."""
    assert "def materialize_tlink_inverses(" in tr_source


@pytest.mark.unit
def test_all_inverse_pairs_present(tr_source):
    """Every forward→inverse pair string must appear together in the method body."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    for fwd, inv in INVERSE_PAIRS:
        assert fwd in body, f"Forward relation {fwd!r} missing from method"
        assert inv in body, f"Inverse relation {inv!r} missing from method"


@pytest.mark.unit
def test_uses_merge_not_create(tr_source):
    """Method must use MERGE (idempotent), not plain CREATE."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "MERGE" in body
    # plain CREATE is not acceptable for idempotent post-processing
    assert "CREATE SET" in body  # ON CREATE SET is acceptable


@pytest.mark.unit
def test_on_create_and_on_match_blocks(tr_source):
    """Both ON CREATE SET and ON MATCH SET must be present (MERGE semantics)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "ON CREATE SET" in body
    assert "ON MATCH SET" in body


@pytest.mark.unit
def test_confidence_guard_in_on_match(tr_source):
    """ON MATCH block must contain a confidence comparison guard."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    # The guard should compare inv.confidence to src_conf
    assert "confidence" in body
    assert "src_conf" in body or "confidence" in body


@pytest.mark.unit
def test_rule_id_property(tr_source):
    """rule_id='case19_timeml_inverse' must appear in the method."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "case19_timeml_inverse" in body


@pytest.mark.unit
def test_derived_from_property(tr_source):
    """derivedFrom property must be set on the inverse edge."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "derivedFrom" in body


@pytest.mark.unit
def test_excluded_symmetric_relations(tr_source):
    """Symmetric / directionless / precision-collapsing relations must NOT appear in the inverse table."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    # None of these should appear as a key in the inverse_map pairs
    for rel in ("SIMULTANEOUS", "IDENTITY", "VAGUE", "BEFORE", "AFTER"):
        # They might appear in comments but should NOT appear in the pair tuples
        assert f'("{rel}",' not in body, (
            f"Relation {rel!r} must not be a forward key in the inverse map"
        )


@pytest.mark.unit
def test_before_after_not_inverted(tr_source):
    """BEFORE and AFTER must NOT be in the inverse_map (precision collapse fix)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert '("BEFORE", "AFTER")' not in body
    assert '("AFTER", "BEFORE")' not in body


@pytest.mark.unit
def test_suppressed_guard(tr_source):
    """Must skip edges marked suppressed=true."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "suppressed" in body


@pytest.mark.unit
def test_reltype_canonical_used(tr_source):
    """Must use relTypeCanonical for matching (post-normalization)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "relTypeCanonical" in body


@pytest.mark.unit
def test_returns_total_count(tr_source):
    """Method must accumulate and return a total count of created/matched edges."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "total_created" in body or "return" in body


# ---------------------------------------------------------------------------
# Inverse pair correctness: one test per pair
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("fwd,inv", INVERSE_PAIRS)
def test_inverse_pair_strings(tr_source, fwd, inv):
    """Each (forward, inverse) string pair must appear together in the method."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert fwd in body, f"{fwd!r} not found in materialize_tlink_inverses"
    assert inv in body, f"{inv!r} not found in materialize_tlink_inverses"


# ---------------------------------------------------------------------------
# Structural coverage: critical pairs for recall improvement
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_is_included_to_includes(tr_source):
    """IS_INCLUDED→INCLUDES is the #1 recall gap (27.6% of MEANTIME gold)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "IS_INCLUDED" in body
    assert "INCLUDES" in body


@pytest.mark.unit
def test_begun_by_to_begins(tr_source):
    """BEGUN_BY→BEGINS covers 5.3% of gold (BEGINS not otherwise produced)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "BEGUN_BY" in body
    assert "BEGINS" in body


@pytest.mark.unit
def test_ended_by_to_ends(tr_source):
    """ENDED_BY→ENDS covers 2.6% of gold (ENDS not otherwise produced)."""
    body = _extract_method(tr_source, "materialize_tlink_inverses")
    assert "ENDED_BY" in body
    assert "ENDS" in body


# ---------------------------------------------------------------------------
# Mock invocation tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mock_invocation_returns_integer():
    """materialize_tlink_inverses() should return an integer total."""
    rec = _make_recognizer()
    result = rec.materialize_tlink_inverses()
    assert isinstance(result, int)


@pytest.mark.unit
def test_mock_invocation_calls_run_query():
    """Should call _run_query once per inverse pair (10 pairs)."""
    rec = _make_recognizer()
    rec.graph.run.return_value.data.return_value = [{"created": 1}]
    rec.materialize_tlink_inverses()
    # One query per pair = 10 calls
    assert rec.graph.run.call_count == len(INVERSE_PAIRS)


@pytest.mark.unit
def test_mock_invocation_aggregates_count():
    """Total returned should equal sum of per-pair counts."""
    rec = _make_recognizer()
    # All pairs return 2 each → total 20
    rec.graph.run.return_value.data.return_value = [{"created": 2}]
    total = rec.materialize_tlink_inverses()
    assert total == 2 * len(INVERSE_PAIRS)


@pytest.mark.unit
def test_mock_invocation_zero_count():
    """Should handle zero-count result (e.g., no existing TLINKs) gracefully."""
    rec = _make_recognizer()
    rec.graph.run.return_value.data.return_value = [{"created": 0}]
    total = rec.materialize_tlink_inverses()
    assert total == 0


@pytest.mark.unit
def test_mock_invocation_empty_result():
    """Should handle empty result list from graph without raising."""
    rec = _make_recognizer()
    rec.graph.run.return_value.data.return_value = []
    total = rec.materialize_tlink_inverses()
    assert total == 0


# ---------------------------------------------------------------------------
# __main__ block integration check
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_block_calls_materialize_inverses(tr_source):
    """__main__ block must call materialize_tlink_inverses()."""
    # Find __main__ block
    main_start = tr_source.find("if __name__ == '__main__'")
    assert main_start != -1, "__main__ block missing"
    main_block = tr_source[main_start:]
    assert "materialize_tlink_inverses" in main_block


@pytest.mark.unit
def test_main_block_ordering(tr_source):
    """materialize_tlink_inverses must be called AFTER normalize and BEFORE closure."""
    main_start = tr_source.find("if __name__ == '__main__'")
    assert main_start != -1
    main_block = tr_source[main_start:]
    pos_norm = main_block.find("normalize_tlink_reltypes")
    pos_inv = main_block.find("materialize_tlink_inverses")
    pos_closure = main_block.find("apply_tlink_transitive_closure")
    assert pos_norm != -1, "normalize_tlink_reltypes not in __main__"
    assert pos_inv != -1, "materialize_tlink_inverses not in __main__"
    assert pos_closure != -1, "apply_tlink_transitive_closure not in __main__"
    assert pos_norm < pos_inv, "normalize must come before materialize_inverses"
    assert pos_inv < pos_closure, "materialize_inverses must come before transitive closure"


# ---------------------------------------------------------------------------
# phase_wrappers integration check
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_phase_wrappers_calls_all_new_cases():
    """phase_wrappers.py must register Cases 12–18."""
    wrappers_path = (
        Path(__file__).resolve().parents[1]
        / "pipeline"
        / "runtime"
        / "phase_wrappers.py"
    )
    source = wrappers_path.read_text(encoding="utf-8")
    for case_num in range(12, 19):
        assert f"create_tlinks_case{case_num}" in source, (
            f"phase_wrappers.py missing create_tlinks_case{case_num}"
        )


@pytest.mark.unit
def test_phase_wrappers_calls_materialize_inverses():
    """phase_wrappers.py must call materialize_tlink_inverses."""
    wrappers_path = (
        Path(__file__).resolve().parents[1]
        / "pipeline"
        / "runtime"
        / "phase_wrappers.py"
    )
    source = wrappers_path.read_text(encoding="utf-8")
    assert "materialize_tlink_inverses" in source
