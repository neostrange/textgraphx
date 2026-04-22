from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = "MATCH (a)-[r:TLINK]->(b) RETURN labels(a), keys(a), a.eiid, a.id, a.doc_id LIMIT 3"
print(graph.run(q).data())
