from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

q = """
MATCH (m1)-[r:TLINK]->(m2)
WHERE m1.doc_id IS NOT NULL 
RETURN count(r) AS with_doc_id
"""
res = graph.run(q).data()
print("TLINKs with m1.doc_id valid:", res)

q2 = """
MATCH (m1)-[r:TLINK]->(m2)
RETURN head(labels(m1)) as l1, head(labels(m2)) as l2, type(r) as type, count(r) as count
"""
res2 = graph.run(q2).data()
print("TLINK distribution:", res2)

q3 = """
MATCH (m1)-[r:TLINK]->(m2)
RETURN m1.doc_id as doc_id, count(r) LIMIT 5
"""
res3 = graph.run(q3).data()
print("TLINK doc_ids:", res3)
