// Coverage and distribution of clause/scope attributes on EventMention.
MATCH (em:EventMention)
RETURN coalesce(em.clauseType, 'UNSET') AS clause_type,
       coalesce(em.scopeType, 'UNSET') AS scope_type,
       count(em) AS mention_count
ORDER BY mention_count DESC, clause_type ASC, scope_type ASC;