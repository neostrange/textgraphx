-- 0007_add_canonical_indexes.cypher
--
-- Add performance indexes for canonical-tier nodes that are frequently
-- filtered or joined on properties not covered by existing constraints.
--
-- Idempotent: IF NOT EXISTS forms are safe to re-run.

-- FrameArgument: headTokenIndex is used to correlate arguments with tokens
CREATE INDEX IF NOT EXISTS FOR (n:FrameArgument) ON (n.headTokenIndex);

-- NamedEntity: headTokenIndex is used to link entities back to anchor tokens
CREATE INDEX IF NOT EXISTS FOR (n:NamedEntity) ON (n.headTokenIndex);

-- TEvent: doc_id isolation scans and TLINK range queries
CREATE INDEX IF NOT EXISTS FOR (n:TEvent) ON (n.doc_id);

-- TIMEX: doc_id isolation scans and TLINK range queries
-- (complementary to the (tid, doc_id) uniqueness constraint in 0004)
CREATE INDEX IF NOT EXISTS FOR (n:TIMEX) ON (n.doc_id);
