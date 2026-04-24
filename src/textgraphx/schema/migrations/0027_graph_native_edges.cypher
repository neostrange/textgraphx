-- 0027_graph_native_edges.cypher
--
-- Backfill graph-native support edges used by downstream reasoning and fusion:
-- - HAS_HEAD_TOKEN  (mention -> head TagOccurrence)
-- - NESTED_IN       (smaller mention span nested in larger mention span)
-- - SAME_AS         (Entity duplicates sharing the same kb_id)
-- - MERGED_INTO     (legacy merge-tracking property -> edge)

// HAS_HEAD_TOKEN for mention-layer nodes
CALL apoc.periodic.iterate(
  """
  MATCH (m)
  WHERE (m:Mention OR m:NamedEntity OR m:EntityMention OR m:CorefMention OR m:NounChunk)
    AND m.headTokenIndex IS NOT NULL
  RETURN m
  """,
  """
  MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
  WHERE d.id = coalesce(m.doc_id, split(coalesce(m.id, ''), '_')[1])
    AND tok.tok_index_doc = m.headTokenIndex
  MERGE (m)-[:HAS_HEAD_TOKEN {source: 'migration_0027'}]->(tok)
  """,
  {batchSize: 500, parallel: false}
);

// NESTED_IN for NamedEntity pairs with same head token and strict span containment
CALL apoc.periodic.iterate(
  """
  MATCH (a:NamedEntity), (b:NamedEntity)
  WHERE coalesce(a.id, '') <> coalesce(b.id, '')
    AND coalesce(a.headTokenIndex, -1) = coalesce(b.headTokenIndex, -2)
    AND coalesce(a.start_tok, a.token_start, a.index) >= coalesce(b.start_tok, b.token_start, b.index)
    AND coalesce(a.end_tok, a.token_end, a.end_index, a.index) <= coalesce(b.end_tok, b.token_end, b.end_index, b.index)
    AND (
      coalesce(a.start_tok, a.token_start, a.index) > coalesce(b.start_tok, b.token_start, b.index)
      OR coalesce(a.end_tok, a.token_end, a.end_index, a.index) < coalesce(b.end_tok, b.token_end, b.end_index, b.index)
    )
  RETURN a, b
  """,
  """
  MERGE (a)-[:NESTED_IN {source: 'migration_0027'}]->(b)
  """,
  {batchSize: 500, parallel: false}
);

// SAME_AS between Entity nodes sharing same kb_id
CALL apoc.periodic.iterate(
  """
  MATCH (e1:Entity), (e2:Entity)
  WHERE e1.kb_id IS NOT NULL AND e2.kb_id IS NOT NULL
    AND e1.kb_id = e2.kb_id
    AND e1.id < e2.id
  RETURN e1, e2
  """,
  """
  MERGE (e1)-[:SAME_AS {source: 'migration_0027'}]->(e2)
  """,
  {batchSize: 500, parallel: false}
);

// MERGED_INTO from legacy property
CALL apoc.periodic.iterate(
  """
  MATCH (src)
  WHERE src.merged_into_id IS NOT NULL
  MATCH (dst {id: src.merged_into_id})
  RETURN src, dst
  """,
  """
  MERGE (src)-[:MERGED_INTO {source: 'migration_0027'}]->(dst)
  """,
  {batchSize: 500, parallel: false}
);

RETURN 'Graph-native support edges backfilled.';