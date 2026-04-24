-- 0026_add_mention_superlabel.cypher
--
-- Backfill :Mention on all mention-layer node labels.
--
-- This is additive and non-destructive.

CALL apoc.periodic.iterate(
  """
  MATCH (m)
  WHERE m:NamedEntity OR m:EntityMention OR m:CorefMention OR m:NominalMention OR m:NounChunk
  RETURN m
  """,
  """
  SET m:Mention
  """,
  {batchSize: 1000, parallel: false}
);

CREATE INDEX mention_doc_id IF NOT EXISTS
FOR (m:Mention) ON (m.doc_id);

RETURN 'Mention super-label backfilled.';