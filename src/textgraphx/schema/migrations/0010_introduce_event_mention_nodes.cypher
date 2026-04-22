-- 0010_introduce_event_mention_nodes.cypher
--
-- Introduce explicit EventMention node type to separate mention-level from canonical-level event semantics.
--
-- MEANTIME semantic model: 
--   EventMention (surface realization with tense, aspect, polarity) -[:REFERS_TO]-> TEvent (canonical event)
--   Frame (SRL predicate) -[:INSTANTIATES]-> EventMention (marks linguistic realization)
--
-- Current TextGraphX state:
--   - TEvent contains both canonical properties (eiid, doc_id) and mention properties (tense, aspect).
--   - Frame is SRL predicate; no explicit connection to mention-level event properties.
--   - DESCRIBES edge links Frame -> TEvent (will become Frame -> EventMention in next phase).
--
-- This migration:
--   1. For each Frame, creates an EventMention node with mention-specific span/properties.
--   2. Creates Frame -[:INSTANTIATES]-> EventMention to mark SRL realization.
--   3. Creates EventMention -[:REFERS_TO]-> TEvent for canonical event identity.
--   4. Clones mention properties from TEvent to EventMention (tense, aspect, etc.) for future decoupling.
--
-- Idempotent: Safe to re-run; uses MERGE and property existence checks.

-- STEP 1: For each Frame that has a DESCRIBES or FRAME_DESCRIBES_EVENT edge to a TEvent,
-- create an EventMention node with frame-scoped identity.
MATCH (f:Frame)-[edge:DESCRIBES|FRAME_DESCRIBES_EVENT]->(event:TEvent)
WITH f, event, COLLECT(DISTINCT type(edge)) as edge_types
WITH f, event,
     f.id as frame_id,
     f.headword as pred,
     COALESCE(f.start_tok, f.startIndex, 0) as start_tok,
     COALESCE(f.end_tok, f.endIndex, 0) as end_tok,
     f.text as pred_text,
     COALESCE(event.doc_id, 'unknown_doc') as doc_id
WITH f, event, frame_id, pred, start_tok, end_tok, pred_text, doc_id,
     frame_id + '_mention' as mention_id
MERGE (em:EventMention {id: mention_id})
SET em.pred = pred,
    em.start_tok = start_tok,
    em.end_tok = end_tok,
    em.text = pred_text,
    em.doc_id = doc_id,
    em.frame_id = frame_id,
    -- Clone mention-level properties from TEvent (will be moved here in property enrichment phase)
    em.tense = event.tense,
    em.aspect = event.aspect,
    em.class = event.class,
    em.epos = event.epos,
    em.form = event.form,
    em.pos = event.pos,
    em.modality = event.modality,
    em.polarity = event.polarity
WITH f, event, em
MERGE (f)-[:INSTANTIATES]->(em)
RETURN count(*) AS event_mentions_created;

-- STEP 2: Create REFERS_TO relationships from EventMention to canonical TEvent.
MATCH (em:EventMention)
WHERE NOT EXISTS { (em)-[:REFERS_TO]->(t:TEvent) }
WITH em
MATCH (f:Frame {id: em.frame_id})-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(event:TEvent)
WITH em, event
MERGE (em)-[:REFERS_TO]->(event)
RETURN count(*) AS refers_to_links_created;

-- STEP 3: Verify Frame still links to TEvent (for backward compatibility during transition).
-- This ensures existing DESCRIBES/FRAME_DESCRIBES_EVENT edges remain valid.
MATCH (f:Frame)
WHERE NOT EXISTS { (f)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(t:TEvent) }
WITH COLLECT(f) as unlinked_frames
RETURN length(unlinked_frames) as unlinked_frame_count;

RETURN "EventMention introduction complete: Frame nodes now instantiate EventMention nodes which refer to canonical TEvent nodes.";
