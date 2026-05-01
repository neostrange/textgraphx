-- Migration 0028: Frame advisory properties + SRL framework index
--
-- Adds a composite index on Frame(framework, sense) to support efficient
-- retrieval of PropBank / NomBank frames by sense roleset.
-- Also creates an index on Frame(provisional) for gating queries.
--
-- Safe to apply to an existing graph; CREATE INDEX ... IF NOT EXISTS is
-- idempotent.

// Composite index: enables targeted Cypher such as
//   MATCH (f:Frame {framework:'PROPBANK', sense:'attack.01'}) ...
CREATE INDEX frame_framework_sense IF NOT EXISTS
FOR (f:Frame) ON (f.framework, f.sense);

// Single-property index on framework alone (covers queries that filter only
// by framework without sense, e.g. count NOMBANK vs PROPBANK frames).
CREATE INDEX frame_framework IF NOT EXISTS
FOR (f:Frame) ON (f.framework);

// Index on provisional flag for gating-status queries.
CREATE INDEX frame_provisional IF NOT EXISTS
FOR (f:Frame) ON (f.provisional);

// Backfill: tag all Frame nodes that lack framework with 'PROPBANK' (the
// historical default; all frames written before this migration were verbal).
MATCH (f:Frame)
WHERE f.framework IS NULL
SET f.framework = 'PROPBANK';
