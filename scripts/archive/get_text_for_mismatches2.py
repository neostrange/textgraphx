from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
print("Total TagOccurrences:", graph.run(f"MATCH (t:TagOccurrence) RETURN count(t) as c").data())
print("Sample TagOccurrence:", graph.run(f"MATCH (t:TagOccurrence) RETURN properties(t) LIMIT 1").data())

