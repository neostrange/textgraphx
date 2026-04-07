// Coverage of entity mentions enriched with entityState situational signals.
MATCH (em:EntityMention)
WITH count(em) AS total_entity_mentions,
     count(CASE WHEN coalesce(trim(toString(em.entityState)), '') <> '' THEN 1 END) AS entity_mentions_with_state
RETURN total_entity_mentions,
       entity_mentions_with_state,
       CASE
           WHEN total_entity_mentions = 0 THEN 0.0
           ELSE toFloat(entity_mentions_with_state) / toFloat(total_entity_mentions)
       END AS coverage_ratio;
