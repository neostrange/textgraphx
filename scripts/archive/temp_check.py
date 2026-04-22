from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
cols = graph.run("MATCH (m:CorefMention) RETURN labels(m) AS lbls").data()
for c in cols[:5]: print(c)
