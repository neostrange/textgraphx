// Distribution of entityStateType labels for enriched entity mentions.
MATCH (em:EntityMention)
WHERE coalesce(trim(toString(em.entityState)), '') <> ''
WITH coalesce(nullif(trim(toString(em.entityStateType)), ''), 'STATE') AS entity_state_type,
     count(em) AS mention_count
RETURN entity_state_type,
       mention_count
ORDER BY mention_count DESC, entity_state_type ASC;
