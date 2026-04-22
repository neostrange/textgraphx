from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = """
MATCH p = shortestPath((at:AnnotatedText {id: '61327'})-[*1..5]-(e:TEvent))
WHERE NOT 'TLINK' IN [rel in relationships(p) | type(rel)]
RETURN [n in nodes(p) | head(labels(n))], [rel in relationships(p) | type(rel)] LIMIT 2
"""
print("Shortest Semantic path:", graph.run(q).data())
