"""Tests for Step 4: role normalization provenance in _link_argument_to_frame.

Verifies that the SRLProcessor stores the canonical role label on the
FrameArgument NODE (a.type / a.raw_role) as well as on the PARTICIPANT edge,
so downstream Cypher matching fa.type IN ['ARG0','ARG1',...] works correctly
even when the raw label carried a C-/R- prefix or -PRD suffix.

No live Neo4j required: source-inspection only.
"""
from pathlib import Path

import pytest

SRL_PATH = (
    Path(__file__).resolve().parents[1]
    / "text_processing_components"
    / "SRLProcessor.py"
)


@pytest.fixture(scope="module")
def srl_source() -> str:
    return SRL_PATH.read_text(encoding="utf-8")


def _extract_method(source: str, method_name: str) -> str:
    start = source.find(f"def {method_name}(")
    assert start != -1, f"{method_name!r} not found in source"
    next_def = source.find("\n    def ", start + len(method_name))
    end = next_def if next_def != -1 else len(source)
    return source[start:end]


@pytest.fixture(scope="module")
def link_src(srl_source):
    return _extract_method(srl_source, "_link_argument_to_frame")


# ---------------------------------------------------------------------------
# Node-level provenance properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNodeTypeProvenanceInLink:
    def test_sets_a_type_to_canonical(self, link_src):
        """FrameArgument node a.type must be set to the canonical (normalized) label."""
        assert "a.type = $canonical" in link_src

    def test_sets_a_raw_role_on_node(self, link_src):
        """FrameArgument node must preserve raw label in a.raw_role."""
        assert "a.raw_role = $raw" in link_src

    def test_node_set_before_participant_merge(self, link_src):
        """SET on node must precede the PARTICIPANT MERGE so it is always written."""
        pos_set = link_src.find("a.type = $canonical")
        pos_merge = link_src.find("MERGE (a)-[r:PARTICIPANT]")
        assert pos_set != -1 and pos_merge != -1
        assert pos_set < pos_merge, \
            "a.type = $canonical must appear before MERGE (a)-[r:PARTICIPANT]"


# ---------------------------------------------------------------------------
# Edge-level provenance properties (existing, regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEdgeTypeProvenanceInLink:
    def test_participant_edge_type_canonical(self, link_src):
        assert "r.type = $canonical" in link_src

    def test_participant_edge_raw_role(self, link_src):
        assert "r.raw_role = $raw" in link_src

    def test_has_frame_argument_edge_type_canonical(self, link_src):
        assert "cr.type = $canonical" in link_src

    def test_has_frame_argument_edge_raw_role(self, link_src):
        assert "cr.raw_role = $raw" in link_src


# ---------------------------------------------------------------------------
# normalize_role invoked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_link_method_calls_normalize_role(link_src):
    """_link_argument_to_frame must delegate normalization to normalize_role."""
    assert "normalize_role" in link_src


@pytest.mark.unit
def test_link_method_uses_norm_canonical(link_src):
    """Canonical label must be sourced from the normalize_role result."""
    assert "norm.canonical" in link_src


@pytest.mark.unit
def test_link_method_uses_norm_raw(link_src):
    """Raw label must be sourced from the normalize_role result."""
    assert "norm.raw" in link_src
