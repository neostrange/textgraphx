with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

import re

old_cypher = """            WITH coalesce(mention, src) AS endpoint, evt, r, doc_id
            MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(evt_tok:TagOccurrence)-[:TRIGGERS]->(evt)
            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION]->(endpoint)
            WITH endpoint, evt, r, doc_id, src_tok, evt_tok
            ORDER BY case when toLower(evt_tok.lemma) = toLower(evt.pred) then 1 else 2 end, evt_tok.tok_index_doc ASC
            WITH endpoint, evt, r, src_tok, head(collect(evt_tok)) AS best_evt_head
            WITH endpoint, evt, r,
                 coalesce(endpoint.start_tok, min(src_tok.tok_index_doc)) AS src_start,
                 coalesce(endpoint.end_tok, max(src_tok.tok_index_doc)) AS src_end,
                  best_evt_head.tok_index_doc AS evt_tok_start,
                  best_evt_head.tok_index_doc AS evt_tok_end,"""

new_cypher = """            WITH coalesce(mention, src) AS endpoint, evt, r, doc_id
            OPTIONAL MATCH (evt_m:EventMention)-[:REFERS_TO]->(evt)
            OPTIONAL MATCH (evt_m)<-[:IN_MENTION]-(evt_head_tok:TagOccurrence)
            WITH endpoint, evt, r, doc_id, evt_m, evt_head_tok
            ORDER BY case when toLower(evt_head_tok.lemma) = toLower(evt_m.pred) then 1 else 2 end, evt_head_tok.tok_index_doc ASC
            WITH endpoint, evt, r, doc_id, evt_m, head(collect(evt_head_tok)) AS best_evt_head
            WITH endpoint, evt, r, doc_id, coalesce(best_evt_head.tok_index_doc, evt_m.start_tok) AS evt_tok_start, coalesce(best_evt_head.tok_index_doc, evt_m.end_tok) AS evt_tok_end
            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION]->(endpoint)
            WITH endpoint, evt, r,
                 coalesce(endpoint.start_tok, min(src_tok.tok_index_doc)) AS src_start,
                 coalesce(endpoint.end_tok, max(src_tok.tok_index_doc)) AS src_end,
                  evt_tok_start,
                  evt_tok_end,"""

if old_cypher in text:
    text = text.replace(old_cypher, new_cypher)
    with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
        f.write(text)
    print("Replaced!")
else:
    print("Could not find old cypher!")

