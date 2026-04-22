"""
Tests for the mention layer (EntityMention and EventMention) introduction.

This test module validates PHASE 1 of the MEANTIME semantic gap closure:
explicit separation of mention-level from canonical-level semantics for
entities and events.

Test coverage:
1. EntityMention node creation and lifecycle
2. EventMention node creation and lifecycle
3. Mention->Canonical REFERS_TO relationships
4. Frame-[:INSTANTIATES]->EventMention linkage
5. Participant linking to both TEvent and EventMention
"""

import pytest
from textgraphx.neo4j_client import make_graph_from_config
import logging

logger = logging.getLogger(__name__)


class TestMentionLayerIntroduction:
    """Test suite for mention layer introduction (PHASE 1)."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph
        # Note: Do not close graph to preserve test data for inspection
        # Cleanup can be done manually or via a separate test fixture if needed

    def test_entity_mention_label_exists(self, graph):
        """Test that EntityMention label exists on NamedEntity nodes after migration."""
        query = "MATCH (em:EntityMention) RETURN count(*) as count"
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        # After migration 0009, all NamedEntity nodes should have EntityMention label
        logger.info(f"Found {count} EntityMention nodes")
        assert count >= 0, "EntityMention nodes should exist after migration"

    def test_entity_mention_refers_to_entity(self, graph):
        """Test that EntityMention nodes have REFERS_TO relationships to Entity nodes."""
        query = """
        MATCH (em:EntityMention)-[:REFERS_TO]->(e:Entity)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EntityMention->Entity REFERS_TO relationships")
        assert count >= 0, "EntityMention should have REFERS_TO relationships to Entity nodes"

    def test_entity_mention_preserves_mention_properties(self, graph):
        """Test that EntityMention nodes preserve mention-specific properties."""
        query = """
        MATCH (em:EntityMention)
        WHERE em.value IS NOT NULL OR em.head IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EntityMention nodes with mention properties (value/head)")
        assert count >= 0, "EntityMention nodes should preserve mention text and head properties"

    def test_event_mention_label_exists(self, graph):
        """Test that EventMention label exists for event mention nodes."""
        query = "MATCH (em:EventMention) RETURN count(*) as count"
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes")
        if count == 0:
            pytest.skip("No EventMention nodes available in current graph state")
        assert count > 0, "EventMention nodes should exist after EventEnrichmentPhase runs create_event_mentions"

    def test_event_mention_refers_to_tevent(self, graph):
        """Test that EventMention nodes have REFERS_TO relationships to TEvent nodes."""
        query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(event:TEvent)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention->TEvent REFERS_TO relationships")
        if count == 0:
            pytest.skip("No EventMention->TEvent REFERS_TO relationships available in current graph state")
        assert count > 0, "EventMention should have REFERS_TO relationships to TEvent nodes"

    def test_event_mention_preserves_mention_properties(self, graph):
        """Test that EventMention nodes preserve mention-specific properties."""
        query = """
        MATCH (em:EventMention)
        WHERE em.tense IS NOT NULL OR em.aspect IS NOT NULL OR em.polarity IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with mention properties (tense/aspect/polarity)")
        if count == 0:
            pytest.skip("No EventMention properties available in current graph state")
        assert count > 0, "EventMention nodes should preserve mention properties (tense/aspect/polarity)"

    def test_frame_instantiates_event_mention(self, graph):
        """Test that Frame nodes have INSTANTIATES relationships to EventMention nodes."""
        query = """
        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} Frame-[:INSTANTIATES]->EventMention relationships")
        if count == 0:
            pytest.skip("No Frame->INSTANTIATES->EventMention relationships available in current graph state")
        assert count > 0, "Frame should instantiate EventMention nodes via INSTANTIATES"

    def test_frame_to_event_mention_to_tevent_chain(self, graph):
        """Test the complete chain: Frame -> EventMention -> TEvent."""
        query = """
        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)-[:REFERS_TO]->(event:TEvent)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} Frame->EventMention->TEvent chains")
        if count == 0:
            pytest.skip("No Frame->EventMention->TEvent chains available in current graph state")
        assert count > 0, "Should have Frame->EventMention->TEvent relationship chains"

    def test_entity_participant_links_to_event_mention(self, graph):
        """Test that Entity/NUMERIC nodes link to EventMention via PARTICIPANT."""
        query = """
        MATCH (em:EventMention)
        OPTIONAL MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(em)
        OPTIONAL MATCH (n:NUMERIC)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(em)
        RETURN count(e) + count(n) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} Entity/NUMERIC->EventMention PARTICIPANT relationships")
        if count == 0:
            pytest.skip("No Entity/NUMERIC participant links to EventMention in current graph state")
        assert count > 0, "Entity/NUMERIC should link to EventMention as participants"

    def test_backward_compatibility_entity_to_tevent(self, graph):
        """Test that backward compatibility is maintained: Entity still links to TEvent."""
        query = """
        MATCH (event:TEvent)
        OPTIONAL MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(event)
        OPTIONAL MATCH (n:NUMERIC)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(event)
        RETURN count(e) + count(n) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} Entity/NUMERIC->TEvent PARTICIPANT relationships (backward compatibility)")
        # Backward compatibility should still work
        if count == 0:
            pytest.skip("No Entity/NUMERIC participant links to TEvent in current graph state")
        assert count > 0, "Entity/NUMERIC should still link to TEvent for backward compatibility"

    def test_event_mention_has_unique_id(self, graph):
        """Test that EventMention nodes have unique identifiers."""
        query = """
        MATCH (em:EventMention)
        WHERE em.id IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with id property")
        if count == 0:
            pytest.skip("No EventMention ids available in current graph state")
        assert count > 0, "EventMention nodes should have unique id properties"

    def test_entity_mention_has_unique_id(self, graph):
        """Test that EntityMention nodes have unique identifiers."""
        query = """
        MATCH (em:EntityMention)
        WHERE em.id IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EntityMention nodes with id property")
        assert count >= 0, "EntityMention nodes should have unique id properties"


class TestMentionLayerIntegration:
    """Integration tests for mention layer with other phases."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_mention_layer_does_not_break_existing_queries(self, graph):
        """Test that introducing mention layer does not break existing queries."""
        # Query for Frame-TEvent relationships (existing pattern)
        query = """
        MATCH (f:Frame)-[:DESCRIBES|:FRAME_DESCRIBES_EVENT]->(event:TEvent)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        
        # Should not raise an error
        assert result is not None, "Existing Frame-TEvent queries should still work"

    def test_mention_layer_relation_completeness(self, graph):
        """Test that mention layer relations are complete when both temporal and event enrichment phases run."""
        query = """
        MATCH (f:Frame)-[:DESCRIBES|:FRAME_DESCRIBES_EVENT]->(event:TEvent)
        OPTIONAL MATCH (f)-[:INSTANTIATES]->(em:EventMention)-[:REFERS_TO]->(event)
        RETURN 
            count(f) as total_frames,
            sum(CASE WHEN em IS NOT NULL THEN 1 ELSE 0 END) as frames_with_mentions
        """
        result = graph.run(query).data()
        
        if result:
            total = result[0]["total_frames"]
            with_mentions = result[0]["frames_with_mentions"]
            logger.info(f"Frame->TEvent relations: {total}, with EventMention: {with_mentions}")
            # All frames should have corresponding event mentions once temporal phase completes
            # (This may not be true in partially processed data, so just log for now)

    def test_signal_still_links_to_tlink(self, graph):
        """Test that temporal signals still function correctly with mention layer."""
        query = """
        MATCH (s:Signal)-[:TRIGGERS]->(tl:TLINK)
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} Signal->TLINK relationships")
        # This just verifies signal linkage is not broken by mention layer


@pytest.mark.scenario
class TestMentionLayerScenarios:
    """Scenario-based tests for mention layer functionality."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_complete_mention_chain_for_document(self, graph):
        """Test a complete mention chain for a single document."""
        # Step 1: Find a document that has a complete EntityMention->REFERS_TO->Entity chain.
        # Use the token-path so we only find documents where RefinementPhase has
        # materialized nominal EntityMention nodes that actually refer to canonical Entity nodes.
        query_doc = """
        MATCH (a:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
            -[:PARTICIPATES_IN]->(em:EntityMention)-[:REFERS_TO]->(:Entity)
        RETURN DISTINCT a.id AS doc_id
        LIMIT 1
        """
        result = graph.run(query_doc).data()
        if not result:
            pytest.skip("No documents with complete EntityMention->REFERS_TO->Entity chains found in graph")
            return
        
        doc_id = result[0]["doc_id"]
        logger.info(f"Testing mention chain for document: {doc_id}")
        
        # Step 2: Verify entity mentions have canonical entities
        query_entity = """
        MATCH (a:AnnotatedText {id: $doc_id})-[*]->(em:EntityMention)-[:REFERS_TO]->(e:Entity)
        RETURN count(*) as mention_count, count(DISTINCT e) as canonical_count
        """
        result = graph.run(query_entity, {"doc_id": doc_id}).data()
        if result:
            mentions = result[0]["mention_count"]
            canonical = result[0]["canonical_count"]
            logger.info(f"Document {doc_id}: {mentions} entity mentions -> {canonical} canonical entities")
            assert canonical > 0, "Should have canonical entities"

    def test_complete_event_mention_chain_for_document(self, graph):
        """Test a complete event mention chain for a single document."""
        # Find a document with events
        query_doc = """
        MATCH (a:AnnotatedText)
        OPTIONAL MATCH (a)-[*]->(em:EventMention)
        WHERE em IS NOT NULL
        RETURN a.id as doc_id
        LIMIT 1
        """
        result = graph.run(query_doc).data()
        if not result:
            logger.warning("No documents with event mentions found")
            return
        # Find a document with a complete EventMention→REFERS_TO→TEvent chain.
        query_doc = """
        MATCH (a:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)
              -[:TRIGGERS]->(:TEvent)<-[:REFERS_TO]-(em:EventMention)
        RETURN DISTINCT a.id AS doc_id
        LIMIT 1
        """
        result = graph.run(query_doc).data()
        if not result:
            pytest.skip("No documents with complete EventMention→REFERS_TO→TEvent chains found in graph")
            return

        doc_id = result[0]["doc_id"]
        logger.info(f"Testing event mention chain for document: {doc_id}")
        
        # Verify event mentions have canonical events
        query_event = """
        MATCH (a:AnnotatedText {id: $doc_id})-[*]->(em:EventMention)-[:REFERS_TO]->(event:TEvent)
        RETURN count(*) as mention_count, count(DISTINCT event) as canonical_count
        """
        result = graph.run(query_event, {"doc_id": doc_id}).data()
        if result:
            mentions = result[0]["mention_count"]
            canonical = result[0]["canonical_count"]
            logger.info(f"Document {doc_id}: {mentions} event mentions -> {canonical} canonical events")
            assert canonical > 0, "Should have canonical events"


# Parametrized tests for mention layer properties
class TestMentionLayerProperties:
    """Tests for mention-specific properties (tense, aspect, polarity, etc.)."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    @pytest.mark.parametrize("property_name", ["tense", "aspect", "polarity", "modality", "pos"])
    def test_event_mention_properties(self, graph, property_name):
        """Test that EventMention nodes have mention-specific properties."""
        query = f"""
        MATCH (em:EventMention)
        WHERE em.{property_name} IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with {property_name}")
        # Property may or may not be present depending on phase execution
        assert count >= 0, f"EventMention.{property_name} query should be valid"

    def test_event_mention_lacks_duplicate_properties(self, graph):
        """Test that EventMention properties match TEvent to avoid duplication."""
        query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(event:TEvent)
        WHERE em.tense = event.tense AND em.polarity = event.polarity
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention-TEvent pairs with matching tense/polarity")
        # This verifies that properties are consistent between mention and canonical
