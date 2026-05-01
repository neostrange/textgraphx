-- 0024_normalize_entity_ids.cypher
--
-- Normalize Entity.id values to deterministic, namespace-scoped identifiers.
--
-- Rules:
-- 1) If kb_id exists: id is derived from kb fragment (cross-document stable)
-- 2) If kb_id absent: id is document-scoped content hash to avoid cross-doc false merges
--
-- Idempotent: re-running is a no-op for already normalized ids.

// KB-backed entities: cross-doc stable id
CALL apoc.periodic.iterate(
  """
  MATCH (e:Entity)
  WHERE e.kb_id IS NOT NULL
    AND trim(toString(e.kb_id)) <> ''
    AND (e.id IS NULL OR NOT e.id STARTS WITH 'entity_')
  RETURN e
  """,
  """
  WITH e,
       split(toString(e.kb_id), '/')[-1] AS kb_fragment,
       toLower(coalesce(e.type, 'entity')) AS etype
  SET e.id = 'entity_' + apoc.util.md5([kb_fragment, etype])
  """,
  {batchSize: 500, parallel: false}
);

// Unresolved entities: document-scoped deterministic id
CALL apoc.periodic.iterate(
  """
  MATCH (e:Entity)
  WHERE coalesce(e.kb_id, '') = ''
    AND (e.id IS NULL OR NOT (e.id STARTS WITH 'entity_' OR e.id STARTS WITH 'nominal_'))
  OPTIONAL MATCH (m)-[:REFERS_TO]->(e)
  WITH e, coalesce(m.doc_id, split(coalesce(m.id, ''), '_')[1], '0') AS doc_id,
       toLower(trim(coalesce(e.text, e.value, e.head, e.id, ''))) AS surf,
       toLower(coalesce(e.type, 'entity')) AS etype
  RETURN DISTINCT e, doc_id, surf, etype
  """,
  """
  SET e.id = 'entity_' + toString(doc_id) + '_' + apoc.util.md5([doc_id, surf, etype])
  """,
  {batchSize: 500, parallel: false}
);

CREATE CONSTRAINT unique_entity_id IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

RETURN 'Entity ids normalized.';