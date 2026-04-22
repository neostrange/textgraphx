// Inventory TimexMention contract health for CI and runtime diagnostics.
// DCT is metadata and should not be represented as TimexMention.

CALL {
  MATCH (tm:TimexMention)
  WHERE tm.doc_id IS NULL OR trim(toString(tm.doc_id)) = ''
  RETURN 'missing_doc_id' AS metric, count(tm) AS item_count
}
UNION ALL
CALL {
  MATCH (tm:TimexMention)
  WHERE tm.start_tok IS NULL OR tm.end_tok IS NULL
  RETURN 'missing_span_coordinates' AS metric, count(tm) AS item_count
}
UNION ALL
CALL {
  MATCH (tm:TimexMention)
  WHERE NOT EXISTS { MATCH (tm)-[:REFERS_TO]->(:TIMEX) }
  RETURN 'broken_refers_to_chain' AS metric, count(tm) AS item_count
}
UNION ALL
CALL {
  MATCH (tm:TimexMention)
  WHERE toUpper(trim(coalesce(toString(tm.tid), ''))) IN ['DCT', 'T0']
  RETURN 'dct_timexmention_count' AS metric, count(tm) AS item_count
}
RETURN metric, item_count
ORDER BY metric;
