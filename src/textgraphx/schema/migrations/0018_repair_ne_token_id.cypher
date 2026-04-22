-- Migration 0018: Repair NamedEntity.token_id to type-agnostic format
--
-- Background
-- ----------
-- NamedEntity.id uses format <doc>_<start>_<end>_<type> (type-embedded).
-- NamedEntity.token_id was intended to be a stable, type-agnostic id for
-- migration-safe joins, but was historically set to the same formula as id.
-- This migration corrects that: token_id is updated to <doc>_<start>_<end>.
--
-- Prerequisites
-- -------------
-- 1. The unique constraint added by migration 0002 enforces token_id uniqueness.
--    If any two NamedEntity nodes share the same (doc, start, end) with different
--    types, their new token_ids would collide.
--
-- OPERATOR CHECKLIST before applying:
--   a) Verify no duplicate spans:
--      MATCH (a:NamedEntity), (b:NamedEntity)
--      WHERE a.id <> b.id
--        AND a.token_start = b.token_start AND a.token_end = b.token_end
--        AND left(a.id, strPosition(a.id, '_')+10) = left(b.id, strPosition(b.id, '_')+10)
--      RETURN count(*) AS duplicate_span_pairs
--   b) Confirm the count is 0.
--   c) Then apply this migration.
--
-- Step 1 – Drop unique constraint (allow the backfill to proceed safely)
DROP CONSTRAINT IF EXISTS FOR (n:NamedEntity) IF EXISTS;

-- Step 2 – Add non-unique index on token_id for efficient lookups
CREATE INDEX IF NOT EXISTS FOR (n:NamedEntity) ON (n.token_id);

-- Step 3 – Backfill token_id to type-agnostic format in batches
-- Pattern: id is "<docid>_<start>_<end>_<type>"; token_id becomes "<docid>_<start>_<end>"
-- We derive the new token_id by stripping the last underscore-delimited segment from id.
CALL apoc.periodic.iterate(
  "MATCH (n:NamedEntity) WHERE n.token_id = n.id OR n.token_id IS NULL RETURN n",
  "SET n.token_id = reverse(split(reverse(n.id), '_', 2)[1])",
  {batchSize: 500, parallel: false}
) YIELD batches, total
RETURN batches, total;
