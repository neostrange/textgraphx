// 0005_backfill_canonical_span_fields.cypher
//
// Idempotent backfill of canonical span fields (start_tok, end_tok) onto all
// canonical-tier span-bearing nodes that were written before the forward writers
// were updated in Milestone 1.
//
// Strategy:
//   - WHERE n.start_tok IS NULL  guard makes each block safe to re-run.
//   - Values are derived from the legacy source field for each label.
//   - TIMEX and TEvent derive token bounds by following the existing
//     (TagOccurrence)-[:TRIGGERS]->(temporal_node) relationships.
//   - NounChunk has only a start token in legacy storage; end_tok is left
//     unset when it cannot be derived.

// --- Frame (legacy: startIndex / endIndex) ---
MATCH (n:Frame)
WHERE n.start_tok IS NULL AND n.startIndex IS NOT NULL
SET n.start_tok = n.startIndex,
    n.end_tok   = n.endIndex;

// --- FrameArgument (legacy: startIndex / endIndex) ---
MATCH (n:FrameArgument)
WHERE n.start_tok IS NULL AND n.startIndex IS NOT NULL
SET n.start_tok = n.startIndex,
    n.end_tok   = n.endIndex;

// --- Antecedent (legacy: startIndex / endIndex) ---
MATCH (n:Antecedent)
WHERE n.start_tok IS NULL AND n.startIndex IS NOT NULL
SET n.start_tok = n.startIndex,
    n.end_tok   = n.endIndex;

// --- CorefMention (legacy: startIndex / endIndex) ---
MATCH (n:CorefMention)
WHERE n.start_tok IS NULL AND n.startIndex IS NOT NULL
SET n.start_tok = n.startIndex,
    n.end_tok   = n.endIndex;

// --- NamedEntity (legacy: start_index / end_index, with token_start / token_end preferred) ---
MATCH (n:NamedEntity)
WHERE n.start_tok IS NULL AND n.start_index IS NOT NULL
SET n.start_tok = coalesce(n.token_start, n.start_index),
    n.end_tok   = coalesce(n.token_end,   n.end_index);

// --- NounChunk (legacy: index stores start token; no legacy end field) ---
MATCH (n:NounChunk)
WHERE n.start_tok IS NULL AND n.index IS NOT NULL
SET n.start_tok = n.index;

// --- TIMEX: derive token bounds from TagOccurrence graph traversal ---
MATCH (tok:TagOccurrence)-[:TRIGGERS]->(t:TIMEX)
WITH t, min(tok.tok_index_doc) AS st, max(tok.tok_index_doc) AS et
WHERE t.start_tok IS NULL
SET t.start_tok = st,
    t.end_tok   = et;

// --- TEvent: derive token bounds from TagOccurrence graph traversal ---
MATCH (tok:TagOccurrence)-[:TRIGGERS]->(e:TEvent)
WITH e, min(tok.tok_index_doc) AS st, max(tok.tok_index_doc) AS et
WHERE e.start_tok IS NULL
SET e.start_tok = st,
    e.end_tok   = et;
