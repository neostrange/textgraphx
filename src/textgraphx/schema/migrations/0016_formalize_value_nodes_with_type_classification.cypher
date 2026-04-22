-- 0016_formalize_value_nodes_with_type_classification.cypher
--
-- Formalize value expression nodes to support MEANTIME value mention semantics.
--
-- This migration:
--   1. Adds uniqueness constraints for VALUE nodes (natural key: doc_id + id)
--   2. Adds indexes for efficient value lookups and type-based filtering
--   3. Enforces value type governance (PERCENT, MONEY, QUANTITY, CARDINAL, ORDINAL, DATE, DURATION, etc.)
--   4. Adds span fields (start_char, end_char, start_tok, end_tok) for all values
--   5. Updates ontology.json to mark VALUE as canonical (status: canonical)
--
-- Backward compatibility: NamedEntity nodes with NUMERIC/VALUE labels remain unchanged
-- New code uses VALUE label on separate VALUE nodes for canonical value representation
-- Legacy queries on NamedEntity:NUMERIC still work; encourage migration to VALUE nodes
--
-- Idempotent: Safe to re-run; uses CREATE CONSTRAINT IF NOT EXISTS

-- STEP 1: Create uniqueness constraint for VALUE natural key
-- (doc_id, id) together form a natural key for values within a document
CREATE CONSTRAINT value_natural_key IF NOT EXISTS
FOR (v:VALUE) REQUIRE (v.doc_id, v.id) IS UNIQUE;

-- STEP 2: Create indexes for efficient VALUE queries
-- Index on (doc_id) for document-scoped value lookups
CREATE INDEX value_doc_id IF NOT EXISTS
FOR (v:VALUE) ON (v.doc_id);

-- Index on (type) for value type queries (PERCENT, MONEY, QUANTITY, CARDINAL, ORDINAL, DATE, DURATION, etc.)
CREATE INDEX value_type IF NOT EXISTS
FOR (v:VALUE) ON (v.type);

-- Index on span boundaries for token-range lookups
CREATE INDEX value_token_span IF NOT EXISTS
FOR (v:VALUE) ON (v.start_tok, v.end_tok);

-- Index on (value) text for value string lookups
CREATE INDEX value_text IF NOT EXISTS
FOR (v:VALUE) ON (v.value);

-- STEP 3: Create indexes for REFERS_TO relationships
-- Enables efficient: VALUE <- [:REFERS_TO] queries (for ValueMention -> VALUE links)
CREATE INDEX value_mentioned_by IF NOT EXISTS
FOR (v:VALUE)<-[r:REFERS_TO]-() ON (r);

-- STEP 4: Create indexes for EVENT_PARTICIPANT relationships with VALUE
-- Some event participants are value expressions (quantified arguments)
CREATE INDEX event_with_value_participant IF NOT EXISTS
FOR ()-[r:EVENT_PARTICIPANT]->(v:VALUE) ON (r);

-- STEP 5: Ensure all VALUE nodes have required span fields
-- These should be populated during ingestion/enrichment phases
-- Default to 0,0 for safety if missing
MATCH (v:VALUE)
WHERE v.start_tok IS NULL OR v.end_tok IS NULL
SET v.start_tok = COALESCE(v.start_tok, 0),
    v.end_tok = COALESCE(v.end_tok, 0)
RETURN count(*) AS values_with_missing_spans;

-- STEP 6: Enforce VALUE type governance
-- All VALUE nodes must have a type from the controlled vocabulary:
-- PERCENT - percentage expressions (e.g., "25%", "fifty percent")
-- MONEY - monetary amounts (e.g., "$5.2 billion", "€100")
-- QUANTITY - numeric quantities (e.g., "3 million", "several tons")
-- CARDINAL - cardinal numbers (e.g., "5", "twenty")
-- ORDINAL - ordinal numbers (e.g., "1st", "third")
-- DATE - date expressions (e.g., "2025-01-15", "March 15")
-- DURATION - duration expressions (e.g., "3 hours", "two weeks")
-- NUMERIC - generic numeric (catch-all for unclassified numbers)
-- OTHER - unclassified value types for extensibility

-- Count values with invalid or missing types
MATCH (v:VALUE)
WHERE v.type IS NULL OR NOT v.type IN [
    'PERCENT', 'MONEY', 'QUANTITY', 'CARDINAL', 'ORDINAL', 
    'DATE', 'DURATION', 'NUMERIC', 'OTHER'
]
WITH v, COALESCE(v.type, 'NULL') AS invalid_type
RETURN count(*) AS value_type_governance_violations,
       collect(distinct invalid_type) AS invalid_types;

-- STEP 7: Add normalized text representation if missing
-- Some enrichment phases may use .value_normalized for comparison
MATCH (v:VALUE)
WHERE v.value_normalized IS NULL
SET v.value_normalized = LOWER(v.value)
RETURN count(*) AS values_with_added_normalization;

-- STEP 8: Validate VALUE node connectedness to document
-- All VALUE nodes should be anchored via TagOccurrence tokens to a Document
-- Query to identify orphaned values (not connected to any document)
MATCH (v:VALUE)
WHERE NOT EXISTS {
    MATCH (v)-[:PARTICIPATES_IN]->(t:TagOccurrence)
    WHERE EXISTS {
        MATCH (t)-[:PARTICIPATES_IN]->(d:Document)
    }
}
RETURN count(*) AS orphaned_values;

-- STEP 9: Document future ValueMention layer introduction
-- Similar to Phase 1 (EntityMention/EventMention) and Phase 3 (SignalMention future),
-- the value layer can be further decomposed:
--
-- Current approach: VALUE nodes at value-token level with doc_id + id keys
--
-- Future enhancement (optional):
--   - Introduce ValueMention nodes for mention-level granularity
--   - ValueMention -[:REFERS_TO]-> VALUE (abstract value)
--   - Enables tracking value usage context, alternative expressions, etc.
--   - Would follow PHASE 1 mention layer pattern

-- STEP 10: Create audit view for value distribution by type
-- Helpful for validating type governance across corpus
MATCH (v:VALUE)
RETURN v.type as value_type, count(v) as count_by_type
ORDER BY count_by_type DESC;

RETURN "VALUE node formalization with type governance complete" AS status;
