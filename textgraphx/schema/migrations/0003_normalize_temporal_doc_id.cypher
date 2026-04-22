-- 0003_normalize_temporal_doc_id.cypher
-- Normalize temporal-layer doc_id values to integer when possible.
-- Safe/idempotent: converts only numeric-like values.

MATCH (t:TIMEX)
WHERE t.doc_id IS NOT NULL AND toString(t.doc_id) =~ '^[0-9]+$'
SET t.doc_id = toInteger(toString(t.doc_id));

MATCH (e:TEvent)
WHERE e.doc_id IS NOT NULL AND toString(e.doc_id) =~ '^[0-9]+$'
SET e.doc_id = toInteger(toString(e.doc_id));
