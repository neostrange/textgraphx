from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (d:AnnotatedText) RETURN d.id, type(d.id) LIMIT 1").data()
print(res)
