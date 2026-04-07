// Count missing identity fields on canonical span-bearing mention nodes.
MATCH (ne:NamedEntity)
WHERE ne.token_id IS NULL
   OR ne.token_start IS NULL
   OR ne.token_end IS NULL
RETURN 'NamedEntity_token_identity_missing' AS identity_rule,
       count(ne) AS violation_count
UNION ALL
MATCH (em:EntityMention)
WHERE em.doc_id IS NULL
   OR em.start_tok IS NULL
   OR em.end_tok IS NULL
RETURN 'EntityMention_doc_span_identity_missing' AS identity_rule,
       count(em) AS violation_count
UNION ALL
MATCH (em:EventMention)
WHERE em.token_id IS NULL
   OR em.token_start IS NULL
   OR em.token_end IS NULL
RETURN 'EventMention_token_identity_missing' AS identity_rule,
       count(em) AS violation_count
ORDER BY identity_rule ASC;
