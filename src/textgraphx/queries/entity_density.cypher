// Per-document entity/event/timex density snapshot.
MATCH (doc:AnnotatedText)
OPTIONAL MATCH (doc)-[:MENTIONS]->(em:EntityMention)
WITH doc, count(DISTINCT em) AS entity_mentions
OPTIONAL MATCH (doc)-[:MENTIONS]->(ev:EventMention)
WITH doc, entity_mentions, count(DISTINCT ev) AS event_mentions
OPTIONAL MATCH (doc)-[:MENTIONS]->(tm:TimexMention)
RETURN doc.id AS document_id,
       entity_mentions,
       event_mentions,
       count(DISTINCT tm) AS timex_mentions
ORDER BY entity_mentions DESC, event_mentions DESC, document_id ASC;