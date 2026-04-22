// Per-document coarse invariants across main node families
MATCH (d:AnnotatedText)
OPTIONAL MATCH (d)-[:CONTAINS_SENTENCE]->(s:Sentence)
OPTIONAL MATCH (s)-[:HAS_TOKEN]->(t:TagOccurrence)
OPTIONAL MATCH (t)-[:TRIGGERS]->(ev:TEvent)
OPTIONAL MATCH (t)-[:TRIGGERS]->(tx:TIMEX)
RETURN d.id AS doc_id,
       count(DISTINCT s) AS sentence_count,
       count(DISTINCT t) AS token_count,
       count(DISTINCT ev) AS tevent_count,
       count(DISTINCT tx) AS timex_count
ORDER BY doc_id;
