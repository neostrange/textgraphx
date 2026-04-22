import re
with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

old_query = """            MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(evt_tok:TagOccurrence)-[:TRIGGERS]->(evt)"""

new_query = """            OPTIONAL MATCH (m:EventMention)-[:REFERS_TO]->(evt)
            OPTIONAL MATCH (m)<-[:IN_MENTION]-(head_tok:TagOccurrence)
            WITH endpoint, evt, r, doc_id, m, head_tok
            ORDER BY case when toLower(head_tok.lemma) = toLower(m.pred) then 1 else 2 end, head_tok.tok_index_doc ASC
            WITH endpoint, evt, r, doc_id, head(collect(head_tok)) AS evt_tok"""

text = text.replace(old_query, new_query)

if "head(collect(head_tok)) AS evt_tok" in text:
    old_next = """            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION|IN_FRAME]->(endpoint)
              WITH endpoint, evt, r,"""
    new_next = """            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION|IN_FRAME]->(endpoint)
              WITH endpoint, evt, r,"""

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
