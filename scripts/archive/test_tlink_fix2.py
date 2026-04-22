from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

doc_id_str = "61327"
q = """
    MATCH (a)-[r:TLINK]->(b)
    WHERE a.doc_id = toInteger($doc_id) AND b.doc_id = toInteger($doc_id)
    RETURN count(r) AS simple_count
"""
res = graph.run(q, doc_id=doc_id_str).data()
print("Simple query returned count:", res)
