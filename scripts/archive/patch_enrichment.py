with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    text = f.read()
    
# Replace the bad query with the new one
bad_query_start = "MATCH (em:EventMention {doc_id: toInteger($doc_id)})\n        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(trig_tok:TagOccurrence)\n        WHERE trig_tok.tok_index_doc = em.start_tok AND s.doc_id = toInteger($doc_id)\n        WITH em, toLower(coalesce(trig_tok.lemma, em.pred)) AS lemma, trig_tok.pos AS pos"
good_query_start = "MATCH (em:EventMention {doc_id: toInteger($doc_id)})\n        WITH em, toLower(em.pred) AS lemma, coalesce(em.pos, '') AS pos"

if bad_query_start in text:
    text = text.replace(bad_query_start, good_query_start)
    with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
        f.write(text)
    print("Patched successfully.")
else:
    print("String not found! Check contents.")
