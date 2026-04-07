-- 0004_add_timex_natural_key_constraint.cypher
-- Enforce TIMEX natural identity by (tid, doc_id).

CREATE CONSTRAINT IF NOT EXISTS
FOR (t:TIMEX)
REQUIRE (t.tid, t.doc_id) IS UNIQUE;
