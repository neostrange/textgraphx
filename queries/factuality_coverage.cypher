// Coverage of factuality labels on EventMention nodes.
MATCH (em:EventMention)
WITH count(em) AS total_event_mentions,
     count(CASE WHEN em.factuality IS NOT NULL AND trim(toString(em.factuality)) <> '' THEN 1 END) AS event_mentions_with_factuality
RETURN total_event_mentions,
       event_mentions_with_factuality,
       CASE
           WHEN total_event_mentions = 0 THEN 0.0
           ELSE toFloat(event_mentions_with_factuality) / toFloat(total_event_mentions)
       END AS coverage_ratio;
