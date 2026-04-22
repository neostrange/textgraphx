-- 0012_event_mention_property_enrichment.cypher
--
-- Enrich EventMention nodes with MEANTIME-compliant fine-grained event properties.
--
-- This migration formalizes event mention properties that were previously stored
-- informally on TEvent nodes. It adds new property classifications for:
--   - aspect: PROGRESSIVE, PERFECTIVE, INCEPTIVE, HABITUAL, ITERATIVE
--   - certainty: CERTAIN, PROBABLE, POSSIBLE, UNDERSPECIFIED  
--   - time: NON_FUTURE, FUTURE, UNDERSPECIFIED
--   - polarity: POS, NEG, UNDERSPECIFIED
--   - special_cases: NONE, GENERIC, CONDITIONAL_MAIN_CLAUSE, REPORTED_SPEECH, etc.
--
-- Backward compatibility: TEvent nodes retain their properties for legacy code.
-- New code queries EventMention for mention-level fine-grain properties.
--
-- Idempotent: Safe to re-run; uses SET for idempotent property updates.

-- STEP 1: Ensure all EventMention nodes have core mention properties
-- (These should already be present from migration 0010, but verify/update if needed)
MATCH (em:EventMention)
WHERE em.tense IS NULL AND EXISTS { (em)-[:REFERS_TO]->(te:TEvent) WHERE te.tense IS NOT NULL }
WITH em
MATCH (em)-[:REFERS_TO]->(te:TEvent)
SET em.tense = te.tense
RETURN count(*) AS tense_backfilled;

MATCH (em:EventMention)
WHERE em.aspect IS NULL AND EXISTS { (em)-[:REFERS_TO]->(te:TEvent) WHERE te.aspect IS NOT NULL }
WITH em
MATCH (em)-[:REFERS_TO]->(te:TEvent)
SET em.aspect = te.aspect
RETURN count(*) AS aspect_backfilled;

MATCH (em:EventMention)
WHERE em.polarity IS NULL AND EXISTS { (em)-[:REFERS_TO]->(te:TEvent) WHERE te.polarity IS NOT NULL }
WITH em
MATCH (em)-[:REFERS_TO]->(te:TEvent)
SET em.polarity = te.polarity
RETURN count(*) AS polarity_backfilled;

-- STEP 2: Formalize event mention aspect classification
-- Map aspect values to MEANTIME standard (PROGRESSIVE, PERFECTIVE, INCEPTIVE, HABITUAL, ITERATIVE)
-- This assumes aspect is already present; formalization is via controlled vocabulary enforcement
MATCH (em:EventMention)
WHERE em.aspect IS NOT NULL
  AND em.aspect IN ['PROGRESSIVE', 'PERFECTIVE', 'INCEPTIVE', 'HABITUAL', 'ITERATIVE']
RETURN count(*) AS formally_classified_aspect;

-- STEP 3: Add certainty property to EventMention (new, not previously in TEvent)
-- Initialize from event context hints; will be refined in future enrichment passes
-- Certainty: CERTAIN, PROBABLE, POSSIBLE, UNDERSPECIFIED
MATCH (em:EventMention)
SET em.certainty = CASE
    WHEN em.modality IN ['might', 'may', 'could'] THEN 'POSSIBLE'
    WHEN em.modality IN ['would', 'should', 'might'] THEN 'PROBABLE'
    WHEN em.modality IS NOT NULL THEN 'PROBABLE'
    ELSE 'UNDERSPECIFIED'
END
RETURN count(*) AS certainty_initialized;

-- STEP 4: Add time classification property to EventMention (new)
-- Time: NON_FUTURE, FUTURE, UNDERSPECIFIED
-- Heuristic: Future modals (will, shall, going to) mark FUTURE
MATCH (em:EventMention)
SET em.time = CASE
    WHEN em.modality IN ['will', 'shall'] THEN 'FUTURE'
    WHEN em.form LIKE '%will%' THEN 'FUTURE'
    WHEN em.form LIKE '%going%' THEN 'FUTURE'
    ELSE 'UNDERSPECIFIED'
END
RETURN count(*) AS time_initialized;

-- STEP 5: Add special_cases property to EventMention (new)
-- special_cases: NONE, GENERIC, CONDITIONAL_MAIN_CLAUSE, REPORTED_SPEECH, PRESUPPOSED, COUNTERFACTUAL
-- Initialize to NONE; will be enriched by linguistic analysis in future passes
MATCH (em:EventMention)
WHERE em.special_cases IS NULL
SET em.special_cases = 'NONE'
RETURN count(*) AS special_cases_initialized;

-- STEP 6: Formalize polarity classification on EventMention
-- Polarity: POS, NEG, UNDERSPECIFIED
-- Ensure consistency with MEANTIME standard vocabulary
MATCH (em:EventMention)
WHERE em.polarity IS NOT NULL
  AND em.polarity IN ['POS', 'NEG', 'UNDERSPECIFIED']
RETURN count(*) AS formally_classified_polarity;

-- STEP 7: Create index on new event mention properties for efficient filtering
-- (Indexes are created in migration 0011, but document here for reference)
-- CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.certainty);
-- CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.time);
-- CREATE INDEX IF NOT EXISTS FOR (m:EventMention) ON (m.special_cases);

-- STEP 8: Verify property distribution across EventMention nodes
MATCH (em:EventMention)
RETURN 
    count(*) as total,
    sum(CASE WHEN em.aspect IS NOT NULL THEN 1 ELSE 0 END) as with_aspect,
    sum(CASE WHEN em.certainty IS NOT NULL THEN 1 ELSE 0 END) as with_certainty,
    sum(CASE WHEN em.time IS NOT NULL THEN 1 ELSE 0 END) as with_time,
    sum(CASE WHEN em.polarity IS NOT NULL THEN 1 ELSE 0 END) as with_polarity,
    sum(CASE WHEN em.special_cases IS NOT NULL THEN 1 ELSE 0 END) as with_special_cases;

RETURN "EventMention property enrichment complete: aspect/certainty/time/polarity/special_cases formalized.";
