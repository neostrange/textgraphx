from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
doc_id = "61327"
q = f"MATCH (a)-[r:TLINK]->(b) WHERE a.id STARTS WITH '{doc_id}_' AND b.id STARTS WITH '{doc_id}_' RETURN count(r) as c"
print("Prefix query count:", graph.run(q).data())
