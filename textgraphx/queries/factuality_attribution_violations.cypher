// Count missing factuality attribution contract fields on EventMention nodes.
MATCH (em:EventMention)
WHERE em.factuality IS NOT NULL
  AND trim(toString(em.factuality)) <> ''
RETURN count(CASE WHEN em.factualitySource IS NULL OR trim(toString(em.factualitySource)) = '' THEN 1 END) AS missing_source_count,
       count(CASE WHEN em.factualityConfidence IS NULL THEN 1 END) AS missing_confidence_count,
       count(CASE
           WHEN em.factualitySource IS NULL
             OR trim(toString(em.factualitySource)) = ''
             OR em.factualityConfidence IS NULL
           THEN 1
       END) AS missing_contract_count;
