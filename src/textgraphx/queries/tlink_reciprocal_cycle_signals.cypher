// Reciprocal directional TLINK pairs that signal simple temporal cycles.
MATCH (a)-[r1:TLINK]->(b), (b)-[r2:TLINK]->(a)
WHERE id(r1) < id(r2)
  AND coalesce(r1.suppressed, false) = false
  AND coalesce(r2.suppressed, false) = false
WITH coalesce(a.doc_id, a.document_id, b.doc_id, b.document_id) AS document_id,
     coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS rel1,
     coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE') AS rel2,
     CASE
         WHEN a:TEvent THEN 'TEvent'
         WHEN a:TIMEX OR a:Timex3 THEN 'TIMEX'
         WHEN a:EventMention THEN 'EventMention'
         WHEN a:TimexMention THEN 'TimexMention'
         ELSE labels(a)[0]
     END AS source_label,
     CASE
         WHEN b:TEvent THEN 'TEvent'
         WHEN b:TIMEX OR b:Timex3 THEN 'TIMEX'
         WHEN b:EventMention THEN 'EventMention'
         WHEN b:TimexMention THEN 'TimexMention'
         ELSE labels(b)[0]
     END AS target_label
WHERE rel1 = rel2
  AND rel1 IN ['BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'BEGINS', 'BEGUN_BY', 'ENDS', 'ENDED_BY']
RETURN document_id,
       rel1 AS rel_type,
       source_label,
       target_label,
       count(*) AS cycle_count
ORDER BY cycle_count DESC, document_id ASC, rel_type ASC, source_label ASC, target_label ASC;