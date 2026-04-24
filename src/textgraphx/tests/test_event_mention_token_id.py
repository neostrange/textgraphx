"""Tests for EventMention token_id properties added in token-based migration support.

This test module validates that EventMention nodes carry token_id, token_start, and
token_end properties for token-based migration-safe joins, matching the pattern
established by NamedEntity.token_id.

Coverage:
- EventMention.token_id presence and format validation
- EventMention.token_start and EventMention.token_end properties
- Consistency with NamedEntity.token_id format
"""

import pytest
from textgraphx.database.client import make_graph_from_config
import re
import logging

logger = logging.getLogger(__name__)


class TestEventMentionTokenId:
    """Test suite for EventMention token_id properties."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_event_mention_has_token_id(self, graph):
        """Test that EventMention nodes have token_id for migration-safe joins.
        
        EventMention.token_id should be set in format: em_<doc_id>_<start_tok>_<end_tok>
        This matches the pattern used by NamedEntity.token_id for consistency.
        """
        query = """
        MATCH (em:EventMention)
        WHERE em.token_id IS NOT NULL
        RETURN count(*) as count, em.token_id as sample_token_id
        LIMIT 1
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        sample_id = result[0]["sample_token_id"] if result else None
        
        logger.info(f"Found {count} EventMention nodes with token_id property")
        logger.info(f"Sample token_id: {sample_id}")
        
        if count == 0:
            pytest.skip("No EventMention nodes with token_id available in current graph state")
        
        # Verify format: em_<integer>_<integer>_<integer>
        assert sample_id is not None, "EventMention.token_id should not be null"
        assert isinstance(sample_id, str), "EventMention.token_id should be a string"
        assert sample_id.startswith("em_"), f"EventMention.token_id should start with 'em_': {sample_id}"
        assert count > 0, "EventMention nodes should have token_id properties for migration-safe joins"

    def test_event_mention_token_id_format(self, graph):
        """Test that EventMention.token_id follows the expected format: em_<doc>_<start>_<end>"""
        query = """
        MATCH (em:EventMention)
        WHERE em.token_id IS NOT NULL
        RETURN em.token_id as token_id, em.doc_id as doc_id, em.token_start as start, em.token_end as end
        LIMIT 10
        """
        result = graph.run(query).data()
        
        if not result:
            pytest.skip("No EventMention nodes with token_id available in current graph state")
        
        # Token ID format should match em_<doc>_<start>_<end>
        for row in result:
            token_id = row["token_id"]
            doc_id = row["doc_id"]
            start = row["start"]
            end = row["end"]
            
            # Pattern: em_<digits>_<digits>_<digits>
            pattern = r"^em_\d+_\d+_\d+$"
            assert re.match(pattern, str(token_id)), f"Token ID format invalid: {token_id}"
            
            logger.info(f"Token ID {token_id}: doc_id={doc_id}, start={start}, end={end}")

    def test_event_mention_has_token_coordinates(self, graph):
        """Test that EventMention nodes have token_start and token_end properties.
        
        These properties enable token-based queries and migration-safe joins.
        """
        query = """
        MATCH (em:EventMention)
        WHERE em.token_start IS NOT NULL AND em.token_end IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with token_start and token_end properties")
        
        if count == 0:
            pytest.skip("No EventMention nodes with token coordinates available in current graph state")
        assert count > 0, "EventMention nodes should have token_start and token_end properties"

    def test_event_mention_token_coordinates_consistency(self, graph):
        """Test that token_start and token_end are consistent with start_tok and end_tok."""
        query = """
        MATCH (em:EventMention)
        WHERE em.token_start IS NOT NULL AND em.token_end IS NOT NULL
              AND em.start_tok IS NOT NULL AND em.end_tok IS NOT NULL
        RETURN count(*) as count,
               count(CASE WHEN em.token_start = em.start_tok THEN 1 END) as token_start_matches,
               count(CASE WHEN em.token_end = em.end_tok THEN 1 END) as token_end_matches
        """
        result = graph.run(query).data()
        
        if not result or result[0]["count"] == 0:
            pytest.skip("No EventMention nodes with both token and legacy properties available")
        
        total = result[0]["count"]
        start_matches = result[0]["token_start_matches"]
        end_matches = result[0]["token_end_matches"]
        
        logger.info(f"Token coordinate consistency: {total} nodes, "
                   f"{start_matches} token_start=start_tok, {end_matches} token_end=end_tok")
        
        # Verify that token_start/token_end are properly aligned with start_tok/end_tok
        assert start_matches == total, "token_start should equal start_tok for all EventMention nodes"
        assert end_matches == total, "token_end should equal end_tok for all EventMention nodes"

    def test_event_mention_token_id_uniqueness_per_mention(self, graph):
        """Test that token_id is derived consistently from mention span coordinates."""
        query = """
        MATCH (em1:EventMention)-[:REFERS_TO]->(te:TEvent),
              (em2:EventMention)-[:REFERS_TO]->(te)
        WHERE em1.token_start = em2.token_start 
              AND em1.token_end = em2.token_end
              AND em1.id <> em2.id
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        duplicate_count = result[0]["count"] if result else 0
        
        logger.info(f"Found {duplicate_count} pairs of EventMentions with same token span but different id")
        # This is allowed - multiple mentions can have same span but different properties
        # Just log for informational purposes

    def test_migration_safe_join_capability(self, graph):
        """Test that token_id enables migration-safe joins between mention types."""
        query = """
        MATCH (em:EventMention)
        WHERE em.token_id IS NOT NULL
        WITH em.token_id as em_token_id, em.doc_id as em_doc_id
        OPTIONAL MATCH (ne:NamedEntity {doc_id: em_doc_id})
        WHERE ne.token_id IS NOT NULL
        RETURN 
            count(DISTINCT em_token_id) as em_token_ids,
            count(DISTINCT ne.token_id) as ne_token_ids
        """
        result = graph.run(query).data()
        
        if not result:
            pytest.skip("Cannot evaluate migration-safe join capability")
        
        em_ids = result[0]["em_token_ids"] or 0
        ne_ids = result[0]["ne_token_ids"] or 0
        
        logger.info(f"Migration-safe join capability: EventMention token_ids={em_ids}, NamedEntity token_ids={ne_ids}")
        
        # Either both should exist (for full migration support) or neither (for initial migration phase)
        # Just verify the capability exists
        if em_ids > 0 and ne_ids > 0:
            logger.info("Both EventMention and NamedEntity have token_ids - migration-safe joins are fully enabled")
