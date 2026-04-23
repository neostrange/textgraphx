// Distribution of entityStateType labels for enriched entity mentions.
MATCH (em:EntityMention)
WHERE coalesce(trim(toString(em.entityState)), '') <> ''
WITH coalesce(trim(toString(em.entityStateType)), '') AS raw_entity_state_type,
         em
WITH CASE
             WHEN raw_entity_state_type = '' THEN 'STATE'
             ELSE raw_entity_state_type
         END AS entity_state_type,
         count(em) AS mention_count
RETURN entity_state_type,
       mention_count
ORDER BY mention_count DESC, entity_state_type ASC;
