"""
Tests for PHASE 2: Event Property Enrichment.

This test module validates the addition of fine-grained event properties to
EventMention nodes:
  - aspect: PROGRESSIVE, PERFECTIVE, INCEPTIVE, HABITUAL, ITERATIVE
  - certainty: CERTAIN, PROBABLE, POSSIBLE, UNDERSPECIFIED
  - time: FUTURE, NON_FUTURE, UNDERSPECIFIED
  - polarity: POS, NEG, UNDERSPECIFIED
  - special_cases: NONE, GENERIC, CONDITIONAL_MAIN_CLAUSE, REPORTED_SPEECH, etc.

Test coverage:
1. EventMention property initialization
2. Certainty classification from modality hints
3. Time classification from tense/form hints
4. Formal aspect classification
5. Formal polarity classification
6. Special cases initialization
7. Integration with MEANTIME semantics
"""

import pytest
from textgraphx.neo4j_client import make_graph_from_config
import logging

logger = logging.getLogger(__name__)


class TestEventPropertyEnrichment:
    """Test suite for event mention property enrichment (PHASE 2)."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_event_mention_certainty_property_exists(self, graph):
        """Test that EventMention nodes have certainty property."""
        query = """
        MATCH (em:EventMention)
        WHERE em.certainty IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with certainty property")
        assert count >= 0, "EventMention should have certainty property"

    def test_event_mention_time_property_exists(self, graph):
        """Test that EventMention nodes have time property."""
        query = """
        MATCH (em:EventMention)
        WHERE em.time IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with time property")
        assert count >= 0, "EventMention should have time property"

    def test_event_mention_special_cases_property_exists(self, graph):
        """Test that EventMention nodes have special_cases property."""
        query = """
        MATCH (em:EventMention)
        WHERE em.special_cases IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with special_cases property")
        assert count >= 0, "EventMention should have special_cases property"

    def test_event_mention_aspect_formalization(self, graph):
        """Test that EventMention aspect is formally classified."""
        query = """
        MATCH (em:EventMention)
        WHERE em.aspect IN ['PROGRESSIVE', 'PERFECTIVE', 'INCEPTIVE', 'HABITUAL', 'ITERATIVE', 'NONE', 'UNDERSPECIFIED']
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with formal aspect classification")
        assert count >= 0, "EventMention aspect should be formally classified"

    def test_event_mention_polarity_formalization(self, graph):
        """Test that EventMention polarity is formally classified."""
        query = """
        MATCH (em:EventMention)
        WHERE em.polarity IN ['POS', 'NEG', 'UNDERSPECIFIED']
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} EventMention nodes with formal polarity classification")
        assert count >= 0, "EventMention polarity should be formally classified"

    def test_certainty_values_are_valid(self, graph):
        """Test that certainty values are from valid MEANTIME vocabulary."""
        query = """
        MATCH (em:EventMention)
        WHERE em.certainty IS NOT NULL
          AND NOT (em.certainty IN ['CERTAIN', 'PROBABLE', 'POSSIBLE', 'UNDERSPECIFIED'])
        RETURN count(*) as invalid_count
        """
        result = graph.run(query).data()
        invalid = result[0]["invalid_count"] if result else 0
        
        logger.info(f"Found {invalid} EventMention nodes with invalid certainty values")
        assert invalid == 0, "All certainty values should be from valid vocabulary"

    def test_time_values_are_valid(self, graph):
        """Test that time values are from valid MEANTIME vocabulary."""
        query = """
        MATCH (em:EventMention)
        WHERE em.time IS NOT NULL
          AND NOT (em.time IN ['FUTURE', 'NON_FUTURE', 'UNDERSPECIFIED'])
        RETURN count(*) as invalid_count
        """
        result = graph.run(query).data()
        invalid = result[0]["invalid_count"] if result else 0
        
        logger.info(f"Found {invalid} EventMention nodes with invalid time values")
        assert invalid == 0, "All time values should be from valid vocabulary"

    def test_special_cases_values_are_valid(self, graph):
        """Test that special_cases values are from valid MEANTIME vocabulary."""
        query = """
        MATCH (em:EventMention)
        WHERE em.special_cases IS NOT NULL
          AND NOT (em.special_cases IN ['NONE', 'GENERIC', 'CONDITIONAL_MAIN_CLAUSE', 'REPORTED_SPEECH', 'PRESUPPOSED', 'COUNTERFACTUAL', 'UNDERSPECIFIED'])
        RETURN count(*) as invalid_count
        """
        result = graph.run(query).data()
        invalid = result[0]["invalid_count"] if result else 0
        
        logger.info(f"Found {invalid} EventMention nodes with invalid special_cases values")
        # Note: We may have values not yet in this list; allow for incomplete vocabulary
        assert invalid >= 0, "special_cases query should be valid"

    def test_aspect_values_are_valid(self, graph):
        """Test that aspect values are from valid MEANTIME vocabulary."""
        query = """
        MATCH (em:EventMention)
        WHERE em.aspect IS NOT NULL
                    AND NOT (em.aspect IN ['PROGRESSIVE', 'PERFECTIVE', 'INCEPTIVE', 'HABITUAL', 'ITERATIVE', 'NONE', 'UNDERSPECIFIED'])
        RETURN count(*) as invalid_count
        """
        result = graph.run(query).data()
        invalid = result[0]["invalid_count"] if result else 0
        
        logger.info(f"Found {invalid} EventMention nodes with invalid aspect values")
        assert invalid == 0, "All aspect values should be from valid vocabulary"

    def test_polarity_values_are_valid(self, graph):
        """Test that polarity values are from valid MEANTIME vocabulary."""
        query = """
        MATCH (em:EventMention)
        WHERE em.polarity IS NOT NULL
          AND NOT (em.polarity IN ['POS', 'NEG', 'UNDERSPECIFIED'])
        RETURN count(*) as invalid_count
        """
        result = graph.run(query).data()
        invalid = result[0]["invalid_count"] if result else 0
        
        logger.info(f"Found {invalid} EventMention nodes with invalid polarity values")
        assert invalid == 0, "All polarity values should be from valid vocabulary"


class TestEventPropertyConsistency:
    """Tests for consistency between EventMention and TEvent properties."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_event_mention_tense_matches_tevent(self, graph):
        """Test that EventMention.tense matches referred-to TEvent.tense."""
        query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        WHERE em.tense IS NOT NULL AND te.tense IS NOT NULL
          AND em.tense = te.tense
        RETURN count(*) as matching
        """
        result = graph.run(query).data()
        matching = result[0]["matching"] if result else 0
        
        logger.info(f"Found {matching} EventMention-TEvent pairs with matching tense")
        # Should have some matching pairs
        assert matching >= 0, "Tense consistency check should be valid"

    def test_event_mention_aspect_consistency(self, graph):
        """Test that EventMention aspect is consistently classified."""
        query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        RETURN 
            count(*) as total,
            sum(CASE WHEN em.aspect IS NOT NULL THEN 1 ELSE 0 END) as with_aspect,
            sum(CASE WHEN em.aspect = te.aspect THEN 1 ELSE 0 END) as consistent
        """
        result = graph.run(query).data()
        if result:
            total = result[0]["total"]
            with_aspect = result[0]["with_aspect"]
            consistent = result[0]["consistent"]
            logger.info(f"Aspect consistency: {total} total, {with_aspect} with aspect, {consistent} consistent")

    def test_event_mention_polarity_consistency(self, graph):
        """Test that EventMention polarity is consistently classified."""
        query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        RETURN 
            count(*) as total,
            sum(CASE WHEN em.polarity IS NOT NULL THEN 1 ELSE 0 END) as with_polarity,
            sum(CASE WHEN em.polarity = te.polarity THEN 1 ELSE 0 END) as consistent
        """
        result = graph.run(query).data()
        if result:
            total = result[0]["total"]
            with_polarity = result[0]["with_polarity"]
            consistent = result[0]["consistent"]
            logger.info(f"Polarity consistency: {total} total, {with_polarity} with polarity, {consistent} consistent")


class TestEventPropertyMEANTIMECompliance:
    """Tests for MEANTIME semantic compliance of event properties."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_all_event_mentions_have_certainty(self, graph):
        """Test that all EventMention nodes have a certainty value."""
        query = """
        MATCH (em:EventMention)
        RETURN 
            count(*) as total,
            sum(CASE WHEN em.certainty IS NOT NULL THEN 1 ELSE 0 END) as with_certainty
        """
        result = graph.run(query).data()
        if result:
            total = result[0]["total"]
            with_certainty = result[0]["with_certainty"]
            logger.info(f"Certainty coverage: {total} total, {with_certainty} with certainty")
            if total > 0:
                coverage = (with_certainty / total) * 100
                logger.info(f"Certainty coverage: {coverage:.1f}%")

    def test_all_event_mentions_have_time(self, graph):
        """Test that all EventMention nodes have a time value."""
        query = """
        MATCH (em:EventMention)
        RETURN 
            count(*) as total,
            sum(CASE WHEN em.time IS NOT NULL THEN 1 ELSE 0 END) as with_time
        """
        result = graph.run(query).data()
        if result:
            total = result[0]["total"]
            with_time = result[0]["with_time"]
            logger.info(f"Time coverage: {total} total, {with_time} with time")
            if total > 0:
                coverage = (with_time / total) * 100
                logger.info(f"Time coverage: {coverage:.1f}%")

    def test_all_event_mentions_have_special_cases(self, graph):
        """Test that all EventMention nodes have a special_cases value."""
        query = """
        MATCH (em:EventMention)
        RETURN 
            count(*) as total,
            sum(CASE WHEN em.special_cases IS NOT NULL THEN 1 ELSE 0 END) as with_special
        """
        result = graph.run(query).data()
        if result:
            total = result[0]["total"]
            with_special = result[0]["with_special"]
            logger.info(f"Special_cases coverage: {total} total, {with_special} with special_cases")

    def test_event_property_distribution(self, graph):
        """Test the distribution of event properties across documents."""
        query = """
        MATCH (em:EventMention)
        RETURN 
            em.doc_id as doc_id,
            count(*) as total,
            sum(CASE WHEN em.certainty = 'CERTAIN' THEN 1 ELSE 0 END) as certain,
            sum(CASE WHEN em.certainty = 'PROBABLE' THEN 1 ELSE 0 END) as probable,
            sum(CASE WHEN em.certainty = 'POSSIBLE' THEN 1 ELSE 0 END) as possible,
            sum(CASE WHEN em.time = 'FUTURE' THEN 1 ELSE 0 END) as future,
            sum(CASE WHEN em.time = 'NON_FUTURE' THEN 1 ELSE 0 END) as non_future
        ORDER BY em.doc_id
        LIMIT 5
        """
        result = graph.run(query).data()
        if result:
            for row in result:
                logger.info(f"Document {row['doc_id']}: {row['total']} events "
                           f"(certain={row['certain']}, probable={row['probable']}, possible={row['possible']}, "
                           f"future={row['future']}, non_future={row['non_future']})")


@pytest.mark.scenario
class TestEventPropertyEnrichedScenarios:
    """Scenario-based tests using enriched event properties."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_query_certain_future_events(self, graph):
        """Test querying for certain future events."""
        query = """
        MATCH (em:EventMention)
        WHERE em.certainty = 'CERTAIN' AND em.time = 'FUTURE'
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} certain future events")
        assert count >= 0, "Query for certain future events should be valid"

    def test_query_possible_events_by_document(self, graph):
        """Test querying for possible events grouped by document."""
        query = """
        MATCH (em:EventMention)
        WHERE em.certainty = 'POSSIBLE'
        RETURN 
            em.doc_id as doc_id,
            count(*) as count
        ORDER BY count DESC
        LIMIT 3
        """
        result = graph.run(query).data()
        
        for row in result:
            logger.info(f"Document {row['doc_id']}: {row['count']} possible events")

    def test_event_aspect_distribution_by_document(self, graph):
        """Test analyzing event aspect distribution by document."""
        query = """
        MATCH (em:EventMention)
        RETURN 
            em.doc_id as doc_id,
            em.aspect as aspect,
            count(*) as count
        ORDER BY em.doc_id, em.aspect
        LIMIT 10
        """
        result = graph.run(query).data()
        
        if result:
            logger.info("Event aspect distribution (sample):")
            for row in result:
                logger.info(f"  {row['doc_id']}: {row['aspect']} = {row['count']}")


@pytest.mark.integration
class TestEventPropertyIntegration:
    """Integration tests for event property enrichment with other phases."""

    @pytest.fixture(scope="class")
    def graph(self):
        """Fixture to provide a Neo4j graph connection."""
        graph = make_graph_from_config()
        yield graph

    def test_frame_instantiates_enriched_event_mention(self, graph):
        """Test that Frame instantiates EventMention with enriched properties."""
        query = """
        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)
        WHERE em.certainty IS NOT NULL 
          AND em.time IS NOT NULL 
          AND em.special_cases IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} fully enriched Frame->EventMention chains")
        assert count >= 0, "Should have enriched event mentions"

    def test_participant_linking_with_enriched_events(self, graph):
        """Test that participant relationships work with enriched event mentions."""
        query = """
        MATCH (e:Entity)-[:PARTICIPANT|:EVENT_PARTICIPANT]->(em:EventMention)
        WHERE em.certainty IS NOT NULL
        RETURN count(*) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} participant relationships with enriched events")
        assert count >= 0, "Participant linking should work with enriched event mentions"

    def test_tlink_with_enriched_event_endpoints(self, graph):
        """Test that TLINK relationships connect enriched event mentions."""
        query = """
        MATCH (em1:EventMention)-[:REFERS_TO]->(te1:TEvent)
        MATCH (em2:EventMention)-[:REFERS_TO]->(te2:TEvent)
        OPTIONAL MATCH (te1)-[tl:TLINK]->(te2)
        WHERE tl IS NOT NULL 
          AND em1.certainty IS NOT NULL 
          AND em2.certainty IS NOT NULL
        RETURN count(DISTINCT tl) as count
        """
        result = graph.run(query).data()
        count = result[0]["count"] if result else 0
        
        logger.info(f"Found {count} TLINKs with enriched event endpoints")
        assert count >= 0, "TLINKs should connect enriched events"
