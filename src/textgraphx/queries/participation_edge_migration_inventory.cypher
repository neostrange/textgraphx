-- Participation edge migration inventory
-- Returns counts of PARTICIPATES_IN edges missing their IN_FRAME or IN_MENTION alias.
-- Used by runtime diagnostics to track dual-write completeness.

MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
WHERE (n:Frame OR n:FrameArgument) AND NOT (tok)-[:IN_FRAME]->(n)
RETURN 'in_frame_missing' AS metric, count(tok) AS item_count
UNION ALL
MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(n)
WHERE (n:NamedEntity OR n:EntityMention OR n:CorefMention OR n:Antecedent OR n:NounChunk)
  AND NOT (tok)-[:IN_MENTION]->(n)
RETURN 'in_mention_missing' AS metric, count(tok) AS item_count
