-- Migration 0021: Backfill uid on existing Antecedent and CorefMention nodes
--
-- Background
-- ----------
-- Migration 0020 added UID constraints on NamedEntity and EntityMention.
-- The CoreferenceResolver.create_node() was updated to write uid on new
-- Antecedent and CorefMention nodes using make_coref_uid(). Nodes that
-- were written before that code change have no uid property and would be
-- invisible to uid-based lookups.
--
-- This migration backfills uid on all such pre-existing nodes.
--
-- UID formula (mirrors make_coref_uid() in textgraphx/utils/id_utils.py)
-- -----------------------------------------------------------------------
-- prefix  : 'corefmention' for :CorefMention, 'antecedent' for :Antecedent
-- doc_id  : extract from n.id as split(n.id, '_')[1]
--           (node id format is {Type}_{docid}_{start}_{end}, docid is numeric)
-- anchor  : coalesce(n.start_tok, n.startIndex, -1)
-- norm    : toLower(trim(apoc.text.regreplace(coalesce(n.text,''), '\\s+', ' ')))
-- payload : doc_id + '|' + prefix + '|' + norm + '|' + toString(anchor)
-- hash    : left(apoc.util.sha1([payload]), 20)
-- uid     : prefix + '_' + doc_id + '_' + hash
--
-- Note: CorefMention nodes that re-used a NamedEntity node already have
-- uid from their NamedEntity creation path. The WHERE n.uid IS NULL clause
-- ensures those nodes are skipped.
--
-- Prerequisites
-- -------------
-- 1. Migration 0020 has been successfully applied.
-- 2. APOC 4.x+ is available (uses apoc.periodic.iterate and apoc.util.sha1).
--
-- OPERATOR CHECKLIST before applying:
--   a) Check how many nodes need backfill:
--      MATCH (n:Antecedent) WHERE n.uid IS NULL RETURN count(n) AS antecedent_null_uid;
--      MATCH (n:CorefMention) WHERE n.uid IS NULL RETURN count(n) AS coref_null_uid;
--   b) If the counts are non-zero, apply this migration.
--   c) After applying, verify both counts return 0.

-- Step 1 – Backfill uid on Antecedent nodes that pre-date UID hardening
CALL apoc.periodic.iterate(
  "MATCH (n:Antecedent) WHERE n.uid IS NULL AND n.id IS NOT NULL RETURN n",
  "WITH n,
        split(n.id, '_')[1] AS doc_id_str,
        coalesce(n.start_tok, n.startIndex, -1) AS anchor,
        toLower(trim(apoc.text.regreplace(coalesce(n.text, ''), '\\s+', ' '))) AS norm
   WITH n, doc_id_str, anchor, norm,
        left(apoc.util.sha1([doc_id_str + '|antecedent|' + norm + '|' + toString(anchor)]), 20) AS h
   SET n.uid = 'antecedent_' + doc_id_str + '_' + h",
  {batchSize: 500, parallel: false}
) YIELD batches, total
RETURN 'Antecedent' AS label, batches, total;

-- Step 2 – Backfill uid on standalone CorefMention nodes
-- (NamedEntity-reuse nodes already have uid from their NamedEntity creation path)
CALL apoc.periodic.iterate(
  "MATCH (n:CorefMention) WHERE n.uid IS NULL AND n.id IS NOT NULL RETURN n",
  "WITH n,
        split(n.id, '_')[1] AS doc_id_str,
        coalesce(n.start_tok, n.startIndex, -1) AS anchor,
        toLower(trim(apoc.text.regreplace(coalesce(n.text, ''), '\\s+', ' '))) AS norm
   WITH n, doc_id_str, anchor, norm,
        left(apoc.util.sha1([doc_id_str + '|corefmention|' + norm + '|' + toString(anchor)]), 20) AS h
   SET n.uid = 'corefmention_' + doc_id_str + '_' + h",
  {batchSize: 500, parallel: false}
) YIELD batches, total
RETURN 'CorefMention' AS label, batches, total;

RETURN "Migration 0021 complete: uid backfilled on pre-existing Antecedent and CorefMention nodes.";
