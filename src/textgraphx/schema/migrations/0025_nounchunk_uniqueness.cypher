-- 0025_nounchunk_uniqueness.cypher
--
-- Rebuild NounChunk.id to include (doc_id, start_tok, end_tok, headTokenIndex)
-- and enforce uniqueness.
--
-- New canonical shape: nc_<doc>_<start>_<end>_<head>

CALL apoc.periodic.iterate(
  """
  MATCH (nc:NounChunk)
  OPTIONAL MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(nc)
  OPTIONAL MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok)
  WITH nc, d,
       coalesce(nc.start_tok, min(tok.tok_index_doc), -1) AS start_tok,
       coalesce(nc.end_tok, max(tok.tok_index_doc), -1) AS end_tok,
       coalesce(nc.headTokenIndex, coalesce(nc.start_tok, min(tok.tok_index_doc), -1)) AS head_tok,
       coalesce(toString(d.id), split(coalesce(nc.id, ''), '_')[1], '0') AS doc_id
  RETURN nc, doc_id, start_tok, end_tok, head_tok
  """,
  """
  SET nc.id = 'nc_' + toString(doc_id) + '_' + toString(start_tok) + '_' + toString(end_tok) + '_' + toString(head_tok)
  """,
  {batchSize: 500, parallel: false}
);

CREATE CONSTRAINT unique_nounchunk_id IF NOT EXISTS
FOR (nc:NounChunk) REQUIRE nc.id IS UNIQUE;

CREATE INDEX nounchunk_span_idx IF NOT EXISTS
FOR (nc:NounChunk) ON (nc.start_tok, nc.end_tok, nc.headTokenIndex);

RETURN 'NounChunk ids rebuilt and uniqueness enforced.';