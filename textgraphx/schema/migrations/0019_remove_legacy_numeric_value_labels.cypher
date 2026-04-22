-- Migration 0019: Remove legacy NUMERIC and VALUE dynamic labels from NamedEntity nodes
--
-- Background
-- ----------
-- RefinementPhase previously applied extra labels :NUMERIC and :VALUE to
-- selected NamedEntity nodes as transitional markers during canonical VALUE
-- node migration.  These writes are now suppressed (fill_numeric_labels=False)
-- and the resulting labels on existing nodes are deprecated.
--
-- This migration strips those labels from all remaining NamedEntity nodes.
-- It is OPERATOR-TRIGGERED only — do not add it to automated CI pipelines.
--
-- Prerequisites
-- -------------
-- 1. Verify canonical VALUE nodes cover your dataset:
--      MATCH (v:VALUE) RETURN count(v) AS value_node_count
-- 2. Confirm EventEnrichmentPhase no longer depends on :NUMERIC/:VALUE labels
--    (Phase 4/5 code changes must be deployed first).
-- 3. Optionally check counts before removal:
--      MATCH (n:NamedEntity:NUMERIC) RETURN count(n) AS numeric_count
--      MATCH (n:NamedEntity:VALUE)   RETURN count(n) AS value_label_count
--
-- Step 1 – Remove :NUMERIC label
MATCH (n:NamedEntity:NUMERIC)
REMOVE n:NUMERIC;

-- Step 2 – Remove :VALUE dynamic label (leaves canonical VALUE nodes untouched;
--           they are :VALUE nodes, not :NamedEntity:VALUE nodes)
MATCH (n:NamedEntity:VALUE)
REMOVE n:VALUE;
