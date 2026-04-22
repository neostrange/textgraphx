// 0008_backfill_canonical_event_edges.cypher
//
// Milestone 4 (Phase 4a): Introduce canonical edge types to replace overloaded
// DESCRIBES and PARTICIPANT predicates.  This migration is additive only —
// legacy edges are NOT removed.  Writers and readers will be updated in
// subsequent sub-slices to dual-emit/read both forms during the transition window.
//
// New canonical edges created:
//   FRAME_DESCRIBES_EVENT  — Frame -> TEvent  (was: :DESCRIBES)
//   HAS_FRAME_ARGUMENT     — FrameArgument -> Frame  (was: :PARTICIPANT)
//   EVENT_PARTICIPANT      — Entity|NUMERIC|FrameArgument -> TEvent  (was: :PARTICIPANT)
//
// All blocks use MERGE for idempotency and are safe to re-run.

// --- FRAME_DESCRIBES_EVENT: copy each (Frame)-[:DESCRIBES]->(TEvent) edge ---
MATCH (f:Frame)-[:DESCRIBES]->(e:TEvent)
MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(e);

// --- HAS_FRAME_ARGUMENT: copy each (FrameArgument)-[:PARTICIPANT]->(Frame) edge ---
MATCH (fa:FrameArgument)-[:PARTICIPANT]->(f:Frame)
MERGE (fa)-[:HAS_FRAME_ARGUMENT]->(f);

// --- EVENT_PARTICIPANT: copy (Entity|NUMERIC|FrameArgument)-[:PARTICIPANT]->(TEvent) edges ---
// Source type is Entity
MATCH (x:Entity)-[r:PARTICIPANT]->(e:TEvent)
MERGE (x)-[nr:EVENT_PARTICIPANT]->(e)
ON CREATE SET nr.type = r.type, nr.prep = r.prep;

// Source type is NUMERIC
MATCH (x:NUMERIC)-[r:PARTICIPANT]->(e:TEvent)
MERGE (x)-[nr:EVENT_PARTICIPANT]->(e)
ON CREATE SET nr.type = r.type, nr.prep = r.prep;

// Source type is FrameArgument (non-core participants)
MATCH (x:FrameArgument)-[r:PARTICIPANT]->(e:TEvent)
MERGE (x)-[nr:EVENT_PARTICIPANT]->(e)
ON CREATE SET nr.type = r.type, nr.prep = r.prep;
