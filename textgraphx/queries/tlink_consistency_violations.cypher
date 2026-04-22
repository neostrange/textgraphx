// Contradictory unsuppressed TLINK pairs on the same endpoints.
MATCH (a)-[r1:TLINK]->(b), (a)-[r2:TLINK]->(b)
WHERE id(r1) < id(r2)
  AND coalesce(r1.suppressed, false) = false
  AND coalesce(r2.suppressed, false) = false
WITH coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS rel1,
     coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE') AS rel2
WHERE (rel1 = 'BEFORE' AND rel2 = 'AFTER')
   OR (rel1 = 'AFTER' AND rel2 = 'BEFORE')
   OR (rel1 = 'INCLUDES' AND rel2 = 'IS_INCLUDED')
   OR (rel1 = 'IS_INCLUDED' AND rel2 = 'INCLUDES')
   OR (rel1 = 'BEGINS' AND rel2 = 'BEGUN_BY')
   OR (rel1 = 'BEGUN_BY' AND rel2 = 'BEGINS')
   OR (rel1 = 'ENDS' AND rel2 = 'ENDED_BY')
   OR (rel1 = 'ENDED_BY' AND rel2 = 'ENDS')
RETURN rel1 AS rel_type_1,
       rel2 AS rel_type_2,
       count(*) AS conflict_count
ORDER BY conflict_count DESC, rel_type_1 ASC, rel_type_2 ASC;