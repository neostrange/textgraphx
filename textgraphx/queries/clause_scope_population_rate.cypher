// Per-document clause/scope population coverage on EventMention nodes.
MATCH (d:AnnotatedText)
OPTIONAL MATCH (d)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(em:EventMention)
WITH d.id AS doc_id, collect(DISTINCT em) AS mentions
UNWIND CASE WHEN size(mentions) = 0 THEN [null] ELSE mentions END AS em
WITH doc_id,
     count(CASE WHEN em IS NOT NULL THEN 1 END) AS total_mentions,
     count(CASE WHEN em IS NOT NULL AND em.clauseType IS NOT NULL THEN 1 END) AS with_clause,
     count(CASE WHEN em IS NOT NULL AND em.scopeType IS NOT NULL THEN 1 END) AS with_scope
RETURN doc_id,
       total_mentions,
       with_clause,
       with_scope,
       CASE WHEN total_mentions = 0 THEN 0.0 ELSE toFloat(with_clause) / toFloat(total_mentions) END AS clause_coverage,
       CASE WHEN total_mentions = 0 THEN 0.0 ELSE toFloat(with_scope) / toFloat(total_mentions) END AS scope_coverage
ORDER BY doc_id ASC;