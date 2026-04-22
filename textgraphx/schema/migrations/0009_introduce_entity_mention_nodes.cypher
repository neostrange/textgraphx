-- 0009_introduce_entity_mention_nodes.cypher
--
-- Introduce explicit EntityMention node type to separate mention-level from canonical-level entity semantics.
-- 
-- MEANTIME semantic model: EntityMention (surface realization) -[:REFERS_TO]-> Entity (canonical)
--
-- This migration:
--   1. Creates a mapping from each existing NamedEntity to a canonical Entity (if not already present)
--   2. Adds the EntityMention label to NamedEntity nodes (dual-label during transition)
--   3. Ensures REFERS_TO relationships exist between EntityMention and canonical Entity
--
-- Idempotent: Safe to re-run; uses MERGE patterns to avoid duplicates.

-- STEP 1: For each NamedEntity, ensure a canonical Entity exists.
-- Strategy: If NamedEntity has kb_id, use that for canonical identity.
-- Otherwise, create a synthetic Entity from aggregated mention properties.
MATCH (ne:NamedEntity)
WHERE ne.kb_id IS NOT NULL
MERGE (e:Entity {id: ne.kb_id})
SET e.type = ne.type,
    e.kb_id = ne.kb_id,
    e.head = ne.head,
    e.headTokenIndex = ne.headTokenIndex,
    e.syntacticType = ne.syntacticType
WITH ne, e
MERGE (ne)-[:REFERS_TO]->(e)
RETURN count(*) AS entities_with_kb_id;

-- STEP 2: For NamedEntity nodes WITHOUT kb_id, create synthetic canonical Entity.
-- Use doc_id + normalized head + type as a grouping key.
MATCH (ne:NamedEntity)
WHERE ne.kb_id IS NULL
WITH ne,
     ne.id as mention_id,
     COALESCE(ne.doc_id, 'unknown_doc') as doc_id,
     COALESCE(ne.head, ne.value, 'unknown_head') as head_text,
     ne.type as entity_type
WITH ne, mention_id, doc_id, head_text, entity_type,
     apoc.util.md5(['entity_canonical', doc_id, head_text, entity_type]) as synthetic_id
MERGE (e:Entity {id: synthetic_id})
SET e.type = entity_type,
    e.head = head_text,
    e.syntacticType = ne.syntacticType
WITH ne, e
MERGE (ne)-[:REFERS_TO]->(e)
RETURN count(*) AS entities_with_synthetic_id;

-- STEP 3: Add EntityMention label to all NamedEntity nodes (dual-label for backward compatibility).
MATCH (n:NamedEntity)
SET n:EntityMention
RETURN count(*) AS entities_labeled_as_mentions;

RETURN "EntityMention introduction complete: all NamedEntity nodes are now also EntityMention nodes with REFERS_TO links to canonical Entity nodes.";
