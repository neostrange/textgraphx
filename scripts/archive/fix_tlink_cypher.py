import re

with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

# Fix tlink cypher
old_cypher_tlink = """              WITH a, b, doc_id, r, source_labels, target_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN source_labels,
                a_start AS a_start, a_end AS a_end,"""

new_cypher_tlink = """              OPTIONAL MATCH (a_m:EventMention)-[:REFERS_TO]->(a)
              OPTIONAL MATCH (b_m:EventMention)-[:REFERS_TO]->(b)
              OPTIONAL MATCH (a_m)<-[:IN_MENTION]-(a_ht:TagOccurrence)
              OPTIONAL MATCH (b_m)<-[:IN_MENTION]-(b_ht:TagOccurrence)
              WITH a, b, doc_id, r, source_labels, target_labels, a_tok_start, a_tok_end, b_tok_start, b_tok_end, a_m, b_m, a_ht, b_ht
              ORDER BY case when toLower(a_ht.lemma) = toLower(a_m.pred) then 1 else 2 end, a_ht.tok_index_doc ASC, case when toLower(b_ht.lemma) = toLower(b_m.pred) then 1 else 2 end, b_ht.tok_index_doc ASC
              WITH a, b, doc_id, r, source_labels, target_labels, a_tok_start, a_tok_end, b_tok_start, b_tok_end, a_m, b_m, head(collect(a_ht)) AS best_a_head, head(collect(b_ht)) AS best_b_head
              WITH a, b, doc_id, r, source_labels, target_labels,
                  coalesce(best_a_head.tok_index_doc, a_m.start_tok, a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(best_a_head.tok_index_doc, a_m.end_tok, a.end_tok, a.end, a_tok_end) AS a_end,
                  coalesce(best_b_head.tok_index_doc, b_m.start_tok, b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(best_b_head.tok_index_doc, b_m.end_tok, b.end_tok, b.end, b_tok_end) AS b_end
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN source_labels,
                a_start, a_end,"""

if old_cypher_tlink in text:
    text = text.replace(old_cypher_tlink, new_cypher_tlink)
    print("tlink fixed")

old_cypher_glink = """              WITH a, b, doc_id, r, source_labels, target_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
           RETURN source_labels,
                a_start, a_end,"""

if old_cypher_glink in text:
    text = text.replace(old_cypher_glink, new_cypher_tlink)
    print("glink fixed")

old_cypher_slink = """              WITH a, b, doc_id, r, source_labels, target_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN type(r) AS rel_kind,
                source_labels,
                a_start, a_end,"""

new_cypher_slink = """              OPTIONAL MATCH (a_m:EventMention)-[:REFERS_TO]->(a)
              OPTIONAL MATCH (b_m:EventMention)-[:REFERS_TO]->(b)
              OPTIONAL MATCH (a_m)<-[:IN_MENTION]-(a_ht:TagOccurrence)
              OPTIONAL MATCH (b_m)<-[:IN_MENTION]-(b_ht:TagOccurrence)
              WITH a, b, doc_id, r, source_labels, target_labels, a_tok_start, a_tok_end, b_tok_start, b_tok_end, a_m, b_m, a_ht, b_ht
              ORDER BY case when toLower(a_ht.lemma) = toLower(a_m.pred) then 1 else 2 end, a_ht.tok_index_doc ASC, case when toLower(b_ht.lemma) = toLower(b_m.pred) then 1 else 2 end, b_ht.tok_index_doc ASC
              WITH a, b, doc_id, r, source_labels, target_labels, a_tok_start, a_tok_end, b_tok_start, b_tok_end, a_m, b_m, head(collect(a_ht)) AS best_a_head, head(collect(b_ht)) AS best_b_head
              WITH a, b, doc_id, r, source_labels, target_labels,
                  coalesce(best_a_head.tok_index_doc, a_m.start_tok, a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(best_a_head.tok_index_doc, a_m.end_tok, a.end_tok, a.end, a_tok_end) AS a_end,
                  coalesce(best_b_head.tok_index_doc, b_m.start_tok, b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(best_b_head.tok_index_doc, b_m.end_tok, b.end_tok, b.end, b_tok_end) AS b_end
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN type(r) AS rel_kind,
                source_labels,
                a_start, a_end,"""

if old_cypher_slink in text:
    text = text.replace(old_cypher_slink, new_cypher_slink)
    print("slink fixed")

with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
    f.write(text)
