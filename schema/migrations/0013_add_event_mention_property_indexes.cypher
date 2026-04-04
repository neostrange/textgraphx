-- 0013_add_event_mention_property_indexes.cypher
--
-- Add performance indexes for new EventMention properties added in PHASE 2.
--
-- These indexes optimize queries that filter or aggregate by:
--   - certainty (CERTAIN, PROBABLE, POSSIBLE)
--   - time (FUTURE, NON_FUTURE)
--   - special_cases (GENERIC, CONDITIONAL, REPORTED_SPEECH)
--   - aspect (PROGRESSIVE, PERFECTIVE, INCEPTIVE)
--
-- Idempotent: IF NOT EXISTS forms safe for re-run.

-- EventMention property indexes for fine-grained event filtering
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.certainty);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.time);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.special_cases);

-- Extended aspect index for event classification
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.aspect);

-- Composite-style indexes for common joint queries
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.doc_id, m.certainty);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.doc_id, m.polarity);
CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.doc_id, m.time);

RETURN "EventMention property indexes added successfully.";
