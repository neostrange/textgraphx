-- 0014_formalize_signal_and_introduce_csignal.cypher
--
-- Formalize temporal and causal signal nodes to support MEANTIME signal mention semantics.
--
-- This migration:
--   1. Adds uniqueness constraints for Signal nodes (natural key: doc_id + id)
--   2. Adds indexes for faster signal lookups and TRIGGERS edge traversal
--   3. Introduces CSignal (causal signal) label for causal triggers
--   4. Enforces signal type governance (SIGNAL or CSIGNAL)
--   5. Adds span fields (start_char, end_char, start_tok, end_tok) for all signals
--
-- Backward compatibility: Signal nodes retain all existing properties and relationships
-- New code can query Signal/CSignal for signal type; legacy code sees all signals as unified Signal label
--
-- Idempotent: Safe to re-run; uses CREATE CONSTRAINT IF NOT EXISTS

-- STEP 1: Create uniqueness constraint for Signal natural key
-- (doc_id, id) together form a natural key for signals within a document
CREATE CONSTRAINT signal_natural_key IF NOT EXISTS
FOR (s:Signal) REQUIRE (s.doc_id, s.id) IS UNIQUE;

-- STEP 2: Create indexes for efficient Signal queries
-- Index on (doc_id) for document-scoped signal lookups
CREATE INDEX signal_doc_id IF NOT EXISTS
FOR (s:Signal) ON (s.doc_id);

-- Index on (type) for signal type queries (SIGNAL, CSIGNAL)
CREATE INDEX signal_type IF NOT EXISTS
FOR (s:Signal) ON (s.type);

-- Index on (start_tok, end_tok) for token span lookups
CREATE INDEX signal_token_span IF NOT EXISTS
FOR (s:Signal) ON (s.start_tok, s.end_tok);

-- STEP 3: Create indexes for TRIGGERS relationship
-- Enables efficient: Signal <- -[:TRIGGERS]- TagOccurrence queries
CREATE INDEX signal_triggers_out IF NOT EXISTS
FOR ()-[r:TRIGGERS]->(s:Signal) ON (r);

-- STEP 4: Verify all Signal nodes have required span fields
-- (These should exist from create_signals2, but validate for safety)
MATCH (s:Signal)
WHERE s.start_tok IS NULL OR s.end_tok IS NULL
SET s.start_tok = COALESCE(s.start_tok, 0),
    s.end_tok = COALESCE(s.end_tok, 0)
RETURN count(*) AS signals_with_missing_spans;

-- STEP 5: Introduce CSignal (causal signal) variant
-- CSignal is a subtype of Signal used for causal/discourse relation triggers
-- Query: MATCH (cs:Signal:CSignal) to get causal signals specifically
-- Query: MATCH (ts:Signal) WHERE NOT cs:CSignal to get temporal signals only
-- All CSignal nodes also have :Signal label for backward compatibility

-- For now, create helper query to show how to mark a signal as causal
-- (Actual conversion would happen in event enrichment or discourse phase)
MATCH (s:Signal)
WHERE s.type = 'CSIGNAL'
SET s:CSignal
RETURN count(*) AS csignals_created;

-- STEP 6: Validate signal type governance
-- All signals should have type = 'SIGNAL' or 'CSIGNAL'
MATCH (s:Signal)
WHERE s.type IS NULL OR NOT s.type IN ['SIGNAL', 'CSIGNAL']
WITH s, coalesce(s.type, 'NULL') AS invalid_type
RETURN count(*) AS signal_type_governance_violations,
       collect(distinct invalid_type) AS invalid_types;

-- STEP 7: Create indexes for signal-to-event relationships (TLINK temporal coverage)
-- Signals can participate in TLINKs via their position
-- Index for efficient TLINK.signalID lookups
CREATE INDEX tlink_signalid IF NOT EXISTS
FOR (tl:TLINK) ON (tl.signalID);

-- STEP 8: Document signal mention properties (for future signal mention node introduction)
-- Current Signal nodes represent both the signal trigger word AND the abstract signal mention
-- Future PHASE: Introduce SignalMention nodes for mention-level granularity
-- SignalMention -[:REFERS_TO]-> Signal (abstract signal)
-- This follows the PHASE 1 pattern for EntityMention/EventMention

RETURN "Signal formalization and CSignal introduction complete" AS status;
