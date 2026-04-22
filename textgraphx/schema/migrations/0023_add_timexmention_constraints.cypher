-- 0023_add_timexmention_constraints.cypher
--
-- Enforce database-level identity guarantees for TimexMention.
-- This migration formalizes the write-path contract introduced by
-- TemporalPhase TIMEX mention materialization.
--
-- Notes:
-- - TimexMention models in-text temporal mentions.
-- - Document Creation Time (DCT) remains document metadata represented as
--   AnnotatedText-[:CREATED_ON]->TIMEX and is not required to have a TimexMention.
-- - Idempotent for Neo4j 4.x+ via IF NOT EXISTS.

CREATE CONSTRAINT unique_timexmention_id IF NOT EXISTS
FOR (tm:TimexMention) REQUIRE tm.id IS UNIQUE;

CREATE INDEX timexmention_doc_id IF NOT EXISTS
FOR (tm:TimexMention) ON (tm.doc_id);

CREATE INDEX timexmention_doc_tid IF NOT EXISTS
FOR (tm:TimexMention) ON (tm.doc_id, tm.tid);

RETURN "TimexMention constraints and indexes added.";
