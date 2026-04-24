"""M13.2: Cypher Query Optimization Tests."""

import pytest

from textgraphx.cypher_optimizer import (
    CypherOptimizer,
    CypherPatternOptimizer,
    QueryPerformanceContract,
    suggest_optimization_for_phase,
)
from textgraphx.database.cypher_optimizer import CypherOptimizer as CanonicalCypherOptimizer


def test_root_cypher_optimizer_wrapper_reexports_canonical_optimizer():
    assert CypherOptimizer is CanonicalCypherOptimizer


class TestCypherOptimizer:
    """Test CypherOptimizer functionality."""
    
    def test_suggested_indexes_complete(self):
        """Test that all critical node types have indexes."""
        indexes = CypherOptimizer.suggest_indexes()
        
        required_nodes = ("AnnotatedText", "TEvent", "TIMEX", "EntityMention", "Entity")
        for node in required_nodes:
            assert node in indexes, f"Missing indexes for {node}"
    
    def test_create_index_statements(self):
        """Test index creation DDL generation."""
        statements = CypherOptimizer.create_index_statements()
        
        assert len(statements) > 0
        assert all("CREATE INDEX" in stmt for stmt in statements)
        assert any("AnnotatedText" in stmt for stmt in statements)
        assert any("TEvent" in stmt for stmt in statements)


class TestCypherPatternOptimizer:
    """Test pattern-specific optimizations."""
    
    def test_temporal_optimization_patterns(self):
        """Test temporal query optimization suggestions."""
        patterns = CypherPatternOptimizer.optimize_temporal_queries()
        
        assert "doc_scoped_tlink_query" in patterns
        assert "event_to_timex_cardinality" in patterns
        # Should suggest early scoping
        assert "{doc_id: $doc_id}" in patterns["doc_scoped_tlink_query"]
    
    def test_entity_optimization_patterns(self):
        """Test entity query optimization suggestions."""
        patterns = CypherPatternOptimizer.optimize_entity_queries()
        
        assert "entity_resolution_dedup" in patterns
        assert "coreference_chain_collapse" in patterns
    
    def test_aggregation_optimization_patterns(self):
        """Test aggregation query optimization suggestions."""
        patterns = CypherPatternOptimizer.optimize_aggregation_queries()
        
        assert "count_with_conditional" in patterns
        assert "histogram_with_group_by" in patterns


class TestQueryPerformanceContract:
    """Test query performance validation."""
    
    def test_validate_query_within_contract(self):
        """Test that queries under threshold pass."""
        passed, msg = QueryPerformanceContract.validate_query_performance(
            "temporal_TLINK_cardinality",
            actual_duration_ms=500,  # Within 1000ms limit
        )
        
        assert passed
        assert msg is None
    
    def test_validate_query_exceeds_contract(self):
        """Test that slow queries fail validation."""
        passed, msg = QueryPerformanceContract.validate_query_performance(
            "temporal_TLINK_cardinality",
            actual_duration_ms=2000,  # Exceeds 1000ms limit
        )
        
        assert not passed
        assert "exceeds limit" in msg.lower()
    
    def test_validate_unknown_query(self):
        """Test that unknown queries don't fail validation."""
        passed, msg = QueryPerformanceContract.validate_query_performance(
            "unknown_query",
            actual_duration_ms=5000,
        )
        
        assert passed
        assert msg is None
    
    def test_get_optimization_hints(self):
        """Test getting optimization hints for critical queries."""
        hints = QueryPerformanceContract.get_optimization_hints("temporal_TLINK_cardinality")
        
        assert hints is not None
        assert "TEvent(doc_id)" in hints


class TestPhaseOptimizations:
    """Test phase-level optimization recommendations."""
    
    def test_temporal_phase_optimization(self):
        """Test TemporalPhase optimization hints."""
        recs = suggest_optimization_for_phase("TemporalPhase")
        
        assert "query_patterns" in recs
        assert "indexes" in recs
        assert recs["optimization_priority"] == "CRITICAL"
        assert len(recs["indexes"]) > 0
    
    def test_event_enrichment_phase_optimization(self):
        """Test EventEnrichmentPhase optimization hints."""
        recs = suggest_optimization_for_phase("EventEnrichmentPhase")
        
        assert "query_patterns" in recs
        assert "indexes" in recs
        assert recs["optimization_priority"] == "HIGH"
    
    def test_refinement_phase_optimization(self):
        """Test RefinementPhase optimization hints."""
        recs = suggest_optimization_for_phase("RefinementPhase")
        
        assert "query_patterns" in recs
        assert "indexes" in recs
        assert recs["optimization_priority"] == "MEDIUM"
    
    def test_unknown_phase_optimization(self):
        """Test optimization for unknown phase returns empty."""
        recs = suggest_optimization_for_phase("UnknownPhase")
        
        # Should return empty dict, not error
        assert isinstance(recs, dict)
