from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

doc_id_str = "61327"
q = """
    MATCH (a)-[r:TLINK]->(b)
    WHERE (a.doc_id = toInteger($doc_id) OR EXISTS {
                     MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[*1..2]->(a)
                })
      AND (b.doc_id = toInteger($doc_id) OR EXISTS {
                     MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[*1..2]->(b)
                })
    RETURN count(r) AS good_count
"""
res = graph.run(q, doc_id=doc_id_str).data()
print("Fixed query returned count:", res)
