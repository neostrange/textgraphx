from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

doc_id = "61327"
q_bad = """
    MATCH (a)-[r:TLINK]->(b)
    WHERE (a.doc_id = $doc_id OR EXISTS {
                     MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(a)
                })
    RETURN count(r) AS bad_count
"""
print("Bad query count:", graph.run(q_bad, doc_id=doc_id).data())

# Now what happens if we add the path to TEvent?
q_good = """
    MATCH (a)-[r:TLINK]->(b)
    WHERE (a.doc_id = $doc_id OR EXISTS {
                     MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[*1..2]->(a)
                })
    RETURN count(r) AS good_count
"""
print("Good query count:", graph.run(q_good, doc_id=doc_id).data())
