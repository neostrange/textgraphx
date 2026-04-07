MATCH ()-[g:GLINK]->()
RETURN coalesce(g.relType, '') AS reltype,
       count(g) AS glink_count
ORDER BY glink_count DESC, reltype ASC
