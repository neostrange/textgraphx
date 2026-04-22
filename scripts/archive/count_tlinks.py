from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH ()-[r:TLINK]->() RETURN count(r) as count").data()
print("Number of TLINKs in graph:", res[0]['count'])
