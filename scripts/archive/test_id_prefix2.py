from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = f"MATCH (a)-[r:TLINK]->(b) RETURN a.id LIMIT 3"
print(graph.run(q).data())
q2 = f"MATCH (a)-[r:TLINK]->(b) RETURN b.id LIMIT 3"
print(graph.run(q2).data())
