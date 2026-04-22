// Count missing canonical mention/event referential chains.
MATCH (em:EntityMention)
WHERE NOT EXISTS { MATCH (em)-[:REFERS_TO]->(:Entity) }
RETURN 'EntityMention_REFERS_TO_Entity' AS contract,
       count(em) AS violation_count
UNION ALL
MATCH (em:EventMention)
WHERE NOT EXISTS { MATCH (em)-[:REFERS_TO]->(:TEvent) }
RETURN 'EventMention_REFERS_TO_TEvent' AS contract,
       count(em) AS violation_count
UNION ALL
MATCH (f:Frame)
WHERE EXISTS { MATCH (f)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(:TEvent) }
  AND NOT EXISTS { MATCH (f)-[:INSTANTIATES]->(:EventMention) }
RETURN 'Frame_INSTANTIATES_EventMention' AS contract,
       count(DISTINCT f) AS violation_count
ORDER BY contract ASC;
