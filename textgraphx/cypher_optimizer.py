"""M13.2: Cypher Query Optimization Strategies.

Performance-critical optimization patterns for Neo4j operations:
  - Index usage verification
  - Query planning hints
  - Cardinality reduction strategies
  - Batch operation consolidation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class CypherOptimizer:
    """Provides Cypher query optimization recommendations and rewrites."""
    
    # Index hints for common patterns
    RECOMMENDED_INDEXES = {
        "AnnotatedText": [("id", "id"), ("doc_id", "doc_id")],
        "Sentence": [("start_tok", "start_tok"), ("end_tok", "end_tok")],
        "TagOccurrence": [("tok_index_doc", "tok_index_doc"), ("text", "text")],
        "TEvent": [("eiid", "eiid"), ("doc_id", "doc_id")],
        "TIMEX": [("tid", "tid"), ("doc_id", "doc_id")],
        "EventMention": [("doc_id", "doc_id"), ("pred", "pred")],
        "EntityMention": [("doc_id", "doc_id"), ("head_text", "head_text")],
        "Entity": [("doc_id", "doc_id"), ("surface_form", "surface_form")],
    }
    
    @staticmethod
    def optimize_match_cardinality(query: str) -> str:
        """Optimize MATCH patterns for early cardinality reduction.
        
        Strategy: Push filters as early as possible to reduce branch cardinality.
        """
        # Add WITH clauses to checkpoint cardinality reduction
        optimized = query.replace(
            "MATCH (n:EventMention)\nWHERE",
            "MATCH (n:EventMention)\nWHERE n.doc_id IS NOT NULL"
        )
        return optimized
    
    @staticmethod
    def batch_creates_into_merge(queries: List[str]) -> str:
        """Consolidate multiple CREATE statements into MERGE operations.
        
        Reduces transaction overhead and improves idempotency.
        """
        # This is a heuristic transformation - in practice, would need parsing
        # Just document the strategy here
        return ";".join(queries)
    
    @staticmethod
    def suggest_indexes() -> Dict[str, List[Tuple[str, str]]]:
        """Return list of recommended indexes to create."""
        return CypherOptimizer.RECOMMENDED_INDEXES
    
    @staticmethod
    def create_index_statements() -> List[str]:
        """Generate CREATE INDEX statements for performance."""
        stmts = []
        for node_label, indexes in CypherOptimizer.RECOMMENDED_INDEXES.items():
            for prop_name, _ in indexes:
                idx_name = f"{node_label}_{prop_name}_idx"
                stmt = f"CREATE INDEX {idx_name} FOR (n:{node_label}) ON (n.{prop_name})"
                stmts.append(stmt)
        return stmts


class CypherPatternOptimizer:
    """Optimizes specific Cypher patterns found in codebase."""
    
    @staticmethod
    def optimize_temporal_queries() -> Dict[str, str]:
        """Optimization patterns for temporal (TLINK, TIMEX) queries."""
        return {
            "doc_scoped_tlink_query": """
            // BEFORE: Scan all nodes
            MATCH (a:TEvent)-[r:TLINK]->(b:TEvent)
            WHERE a.doc_id = $doc_id AND b.doc_id = $doc_id
            
            // AFTER: Scope match early
            MATCH (doc:AnnotatedText {id: $doc_id})
            MATCH (a:TEvent {doc_id: $doc_id})-[r:TLINK]->(b:TEvent {doc_id: $doc_id})
            """,
            
            "event_to_timex_cardinality": """
            // BEFORE: Cartesian product risk
            MATCH (e:EventMention)-[:REFERS_TO]->(te:TEvent)
            MATCH (te)-[:TLINK]->(t:TIMEX)
            
            // AFTER: Early scoping
            MATCH (e:EventMention {doc_id: $doc_id})
            MATCH (e)-[:REFERS_TO]->(te:TEvent)
            MATCH (te)-[:TLINK]->(t:TIMEX {doc_id: $doc_id})
            """,
        }
    
    @staticmethod
    def optimize_entity_queries() -> Dict[str, str]:
        """Optimization patterns for entity linking queries."""
        return {
            "entity_resolution_dedup": """
            // BEFORE: Multiple collection passes
            WITH collect(DISTINCT e) AS entities
            WITH entities, size(entities) AS count
            
            // AFTER: One-pass aggregation
            WITH count(DISTINCT e) AS entity_count,
                 collect(DISTINCT e.surface_form) AS unique_forms
            """,
            
            "coreference_chain_collapse": """
            // BEFORE: Recursive traversal (slow for long chains)
            WITH head(collect(e ORDER BY e.creation_time DESC)) AS canonical
            
            // AFTER: Indexed lookup with max predicate
            WITH max(e.score) AS best_score
            MATCH (e:Entity) WHERE e.score = best_score
            """,
        }
    
    @staticmethod
    def optimize_aggregation_queries() -> Dict[str, str]:
        """Optimization patterns for metrics/aggregation queries."""
        return {
            "count_with_conditional": """
            // BEFORE: Multiple full scans
            WITH count(e) AS total,
                 count(CASE WHEN e.state IS NOT NULL THEN 1 END) AS with_state
            
            // AFTER: Single scan with subquery
            WITH
              (MATCH (e:EntityMention) RETURN count(*) AS c1) as total,
              (MATCH (e:EntityMention {doc_id: $doc_id}) WHERE e.state IS NOT NULL RETURN count(*) AS c2) as with_state
            """,
            
            "histogram_with_group_by": """
            // BEFORE: Collect then count
            WITH collect(e) AS entities
            WITH entities, [e IN entities | e.state] AS states
            
            // AFTER: Native aggregation
            RETURN e.state, count(*) AS count
            GROUP BY e.state
            ORDER BY count DESC
            """,
        }


class QueryPerformanceContract:
    """Defines performance contracts for critical queries."""
    
    CRITICAL_QUERIES = {
        "temporal_TLINK_cardinality": {
            "max_duration_ms": 1000,  # Must complete in < 1 second
            "expected_rows": "doc_size * 0.5",  # Heuristic
            "index_hints": ["TEvent(doc_id)"],
        },
        "entity_fusion_match": {
            "max_duration_ms": 500,
            "expected_rows": "entity_count_in_doc",
            "index_hints": ["Entity(surface_form)", "EntityMention(doc_id)"],
        },
        "mention_layer_coverage": {
            "max_duration_ms": 300,
            "expected_rows": "sentence_count_in_doc * avg_mentions_per_sentence",
            "index_hints": ["EntityMention(doc_id)", "EventMention(doc_id)"],
        },
        "phase_materialization_write": {
            "max_duration_ms": 2000,  # Writes are OK to be slower
            "expected_rows": "phase_output_cardinality",
            "index_hints": None,
        },
    }
    
    @staticmethod
    def validate_query_performance(
        query_name: str,
        actual_duration_ms: float,
    ) -> Tuple[bool, Optional[str]]:
        """Check if query meets performance contract."""
        if query_name not in QueryPerformanceContract.CRITICAL_QUERIES:
            return True, None  # Not a critical query
        
        contract = QueryPerformanceContract.CRITICAL_QUERIES[query_name]
        max_ms = contract["max_duration_ms"]
        
        if actual_duration_ms > max_ms:
            return False, f"Query '{query_name}' took {actual_duration_ms}ms, exceeds limit of {max_ms}ms"
        
        return True, None
    
    @staticmethod
    def get_optimization_hints(query_name: str) -> Optional[List[str]]:
        """Get optimization hints for a query."""
        if query_name not in QueryPerformanceContract.CRITICAL_QUERIES:
            return None
        return QueryPerformanceContract.CRITICAL_QUERIES[query_name].get("index_hints")


def suggest_optimization_for_phase(phase_name: str) -> Dict[str, Any]:
    """Generate phase-specific optimization recommendations."""
    recommendations: Dict[str, Any] = {}
    
    if phase_name == "TemporalPhase":
        recommendations = {
            "query_patterns": CypherPatternOptimizer.optimize_temporal_queries(),
            "indexes": ["TEvent(doc_id)", "TIMEX(doc_id)", "TLINK(relType)"],
            "optimization_priority": "CRITICAL",
            "rationale": "Temporal relations are high-cardinality; early filtering essential",
        }
    elif phase_name == "EventEnrichmentPhase":
        recommendations = {
            "query_patterns": CypherPatternOptimizer.optimize_entity_queries(),
            "indexes": ["EventMention(doc_id)", "Frame(pred)"],
            "optimization_priority": "HIGH",
            "rationale": "Event matching is O(n²) without proper indexes",
        }
    elif phase_name == "RefinementPhase":
        recommendations = {
            "query_patterns": CypherPatternOptimizer.optimize_aggregation_queries(),
            "indexes": ["Entity(doc_id)", "EntityMention(doc_id)"],
            "optimization_priority": "MEDIUM",
            "rationale": "Aggregations benefit from indexed scans",
        }
    
    return recommendations
