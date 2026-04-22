"""Source-inspection tests for EventEnrichmentPhase.link_frameArgument_to_event.

These tests do not require spaCy or a live Neo4j instance; they validate the
Cypher query structure by inspecting the production source file statically.

Backlog item 4: Event-enrichment linking-query validation/refactor.

Coverage:
  - 3-path query structure (direct / via FrameArgument / via EventMention)
  - MERGE idempotency on write paths
  - Relationship types: DESCRIBES, FRAME_DESCRIBES_EVENT, INSTANTIATES
  - Return variables and count patterns
  - PARTICIPATES_IN, PARTICIPANT, TRIGGERS, REFERS_TO relationship navigation
"""

import re
from pathlib import Path

import pytest

EEP_SRC_PATH = Path(__file__).parent.parent / "textgraphx" / "EventEnrichmentPhase.py"


@pytest.fixture(scope="module")
def eep_source() -> str:
    return EEP_SRC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def link_method_source(eep_source: str) -> str:
    """Extract the body of link_frameArgument_to_event from the source."""
    start = eep_source.find("def link_frameArgument_to_event(")
    assert start != -1, "link_frameArgument_to_event method not found"
    # Find the next top-level method definition (4-space indent 'def ')
    next_def = re.search(r"\n    def ", eep_source[start + 10:])
    end = start + 10 + next_def.start() if next_def else len(eep_source)
    return eep_source[start:end]


# ---------------------------------------------------------------------------
# Structural: 3 query paths are present
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreeQueryPaths:
    def test_direct_path_present(self, link_method_source):
        """Path 1: TagOccurrence PARTICIPATES_IN Frame and TRIGGERS TEvent."""
        assert "PARTICIPATES_IN" in link_method_source
        assert "TRIGGERS" in link_method_source

    def test_direct_path_matches_frame_node(self, link_method_source):
        """Path 1 must match a Frame node."""
        assert "f:Frame" in link_method_source or ":Frame" in link_method_source

    def test_via_frame_argument_path_present(self, link_method_source):
        """Path 2: TokenOccurrence -> FrameArgument -> Frame -> TEvent."""
        assert "FrameArgument" in link_method_source
        assert "PARTICIPANT" in link_method_source

    def test_event_mention_path_present(self, link_method_source):
        """Path 3: EventMention -[:REFERS_TO]-> TEvent <- Frame (INSTANTIATES)."""
        assert "EventMention" in link_method_source
        assert "REFERS_TO" in link_method_source

    def test_instantiates_relationship_created(self, link_method_source):
        """Path 3 must MERGE an INSTANTIATES relationship to EventMention."""
        assert "INSTANTIATES" in link_method_source

    def test_at_least_three_query_strings(self, link_method_source):
        """Method should contain at least 3 multi-line MATCH/MERGE Cypher strings."""
        match_count = link_method_source.count("MATCH")
        assert match_count >= 3, (
            f"Expected >=3 MATCH clauses in link_frameArgument_to_event, found {match_count}"
        )


# ---------------------------------------------------------------------------
# Idempotency: MERGE on write paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMergeIdempotency:
    def test_path1_uses_merge_for_describes(self, link_method_source):
        """Path 1 must MERGE (not CREATE) DESCRIBES."""
        assert "MERGE (f)-[:DESCRIBES]->(event)" in link_method_source

    def test_path1_uses_merge_for_frame_describes_event(self, link_method_source):
        """Path 1 must MERGE FRAME_DESCRIBES_EVENT."""
        assert "MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(event)" in link_method_source

    def test_path2_uses_merge_for_describes(self, link_method_source):
        """Path 2 must MERGE DESCRIBES (not CREATE)."""
        # MERGE appears at least twice for DESCRIBES (once per path)
        merge_count = link_method_source.count("MERGE (f)-[:DESCRIBES]->(event)")
        assert merge_count >= 2, (
            f"Expected MERGE for DESCRIBES in both paths, found {merge_count}"
        )

    def test_path3_uses_merge_for_instantiates(self, link_method_source):
        """Path 3 must MERGE INSTANTIATES."""
        assert "MERGE (f)-[:INSTANTIATES]->(em)" in link_method_source

    def test_no_create_statement_in_method(self, link_method_source):
        """CREATE must not appear in this method — only MERGE for idempotency."""
        # Strip Cypher string contents but look at bare CREATE keyword
        bare_create = re.search(r"\bCREATE\b", link_method_source)
        assert bare_create is None, (
            "link_frameArgument_to_event must not use CREATE; use MERGE for idempotency"
        )


# ---------------------------------------------------------------------------
# Relationship types: correct edge labels
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelationshipTypes:
    def test_describes_relationship_type_used(self, link_method_source):
        assert "DESCRIBES" in link_method_source

    def test_frame_describes_event_relationship_type_used(self, link_method_source):
        assert "FRAME_DESCRIBES_EVENT" in link_method_source

    def test_instantiates_relationship_type_used(self, link_method_source):
        assert "INSTANTIATES" in link_method_source

    def test_triggers_relationship_navigated(self, link_method_source):
        assert "TRIGGERS" in link_method_source

    def test_participates_in_relationship_navigated(self, link_method_source):
        assert "PARTICIPATES_IN" in link_method_source

    def test_refers_to_relationship_navigated(self, link_method_source):
        assert "REFERS_TO" in link_method_source

    def test_participant_relationship_navigated(self, link_method_source):
        """FrameArgument path uses PARTICIPANT to reach Frame."""
        assert "PARTICIPANT" in link_method_source


# ---------------------------------------------------------------------------
# Return values: method returns numeric count
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReturnValues:
    def test_paths_1_2_return_linked_count(self, link_method_source):
        """Paths 1 and 2 must project a 'linked' alias for result accumulation."""
        assert "linked" in link_method_source

    def test_path3_returns_instantiates_count(self, link_method_source):
        """Path 3 must project an 'instantiates' alias."""
        assert "instantiates" in link_method_source

    def test_linked_accumulated_from_both_paths(self, link_method_source):
        """The accumulated count must be built with +=."""
        assert "+=" in link_method_source

    def test_method_initialises_linked_to_zero(self, link_method_source):
        """linked counter must be initialised before the loops."""
        # 'linked = 0' or 'linked=0'
        assert re.search(r"linked\s*=\s*0", link_method_source)


# ---------------------------------------------------------------------------
# Source file integrity: method is present and not empty
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMethodIntegrity:
    def test_method_defined_in_source_file(self, eep_source):
        assert "def link_frameArgument_to_event" in eep_source

    def test_source_file_is_readable(self):
        assert EEP_SRC_PATH.exists(), f"Source file not found: {EEP_SRC_PATH}"
        assert EEP_SRC_PATH.stat().st_size > 0

    def test_method_body_non_trivial(self, link_method_source):
        assert len(link_method_source) > 200, "Method body seems too short"
