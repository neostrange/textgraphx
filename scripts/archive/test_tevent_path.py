from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = """
MATCH p = shortestPath((at:AnnotatedText {id: '61327'})-[*1..5]-(e:TEvent))
RETURN [n in nodes(p) | head(labels(n))] LIMIT 1
"""
print("Shortest path:", graph.run(q).data())
