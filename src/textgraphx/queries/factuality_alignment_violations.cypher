// Count factuality mismatches between EventMention and canonical TEvent.
MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
WHERE em.factuality IS NOT NULL
  AND trim(toString(em.factuality)) <> ''
  AND te.factuality IS NOT NULL
  AND trim(toString(te.factuality)) <> ''
  AND toUpper(toString(em.factuality)) <> toUpper(toString(te.factuality))
  AND coalesce(te.factualityConflictFlag, false) = false
RETURN toUpper(toString(em.factuality)) AS mention_factuality,
       toUpper(toString(te.factuality)) AS tevent_factuality,
       count(*) AS violation_count
ORDER BY violation_count DESC, mention_factuality ASC, tevent_factuality ASC;
