-- 0017_backfill_has_lemma_edges.cypher
--
-- Purpose:
--   Backfill canonical HAS_LEMMA edges from legacy TagOccurrence-[:REFERS_TO]->Tag links.
--
-- Properties:
--   - Idempotent: MERGE prevents duplicate HAS_LEMMA edges.
--   - Non-destructive: legacy REFERS_TO lemma links are retained for compatibility.

MATCH (tok:TagOccurrence)-[:REFERS_TO]->(tag:Tag)
MERGE (tok)-[:HAS_LEMMA]->(tag);
