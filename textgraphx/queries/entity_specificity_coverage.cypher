MATCH (m)
WHERE (m:EntityMention OR m:NamedEntity)
WITH count(m) AS total_mentions,
     sum(CASE WHEN coalesce(m.ent_class, m.entClass, '') <> '' THEN 1 ELSE 0 END) AS mentions_with_ent_class
RETURN total_mentions,
       mentions_with_ent_class,
       CASE
           WHEN total_mentions = 0 THEN 0.0
           ELSE toFloat(mentions_with_ent_class) / toFloat(total_mentions)
       END AS coverage_ratio
