-- 0011_add_mention_constraints_and_indexes.cypher
--
-- Add uniqueness constraints and indexes for EntityMention and EventMention nodes.
-- This ensures efficient identity matching and prevents accidental duplicates.
--
-- Idempotent: Uses IF NOT EXISTS forms safe for Neo4j 4.x+.

-- Constraints for EntityMention (dual-label with NamedEntity during transition)
-- EntityMention.id is unique within document scope
CREATE CONSTRAINT unique_entity_mention_id IF NOT EXISTS
FOR (m:EntityMention) REQUIRE m.id IS UNIQUE;

-- Constraints for EventMention
-- EventMention.id is unique (scoped by frame_id + doc_id)
CREATE CONSTRAINT unique_event_mention_id IF NOT EXISTS
FOR (m:EventMention) REQUIRE m.id IS UNIQUE;

-- Indexes for EntityMention
-- Used to filter mentions by document and head token
CREATE INDEX IF NOT EXISTS FOR (m:EntityMention) ON (m.doc_id);
CREATE INDEX IF NOT EXISTS FOR (m:EntityMention) ON (m.headTokenIndex);

-- Indexes for EventMention
-- Used to filter mentions by document and predicate span
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.doc_id);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.start_tok);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.pred);

-- Indexes for Entity (used by EntityMention -[:REFERS_TO]-> Entity)
-- Improve REFERS_TO lookups by canonical entity identity
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.id);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.kb_id);

-- Index for REFERS_TO relationships (speeds up mention -> canonical lookups)
-- This is naturally indexed via the above node-level indexes, but we document
-- the query patterns that rely on them.

RETURN "Mention layer constraints and indexes added successfully.";
