MATCH (m)
WHERE m:EventMention OR m:TEvent
WITH count(m) AS total_event_nodes,
     sum(CASE WHEN coalesce(m.external_ref, m.externalRef, '') <> '' THEN 1 ELSE 0 END) AS event_nodes_with_external_ref
RETURN total_event_nodes,
       event_nodes_with_external_ref,
       CASE
           WHEN total_event_nodes = 0 THEN 0.0
           ELSE toFloat(event_nodes_with_external_ref) / toFloat(total_event_nodes)
       END AS coverage_ratio
