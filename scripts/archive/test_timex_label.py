from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
print("TIMEX count:", graph.run("MATCH (t:TIMEX) RETURN count(t) as c").data())
print("Timex3 count:", graph.run("MATCH (t:Timex3) RETURN count(t) as c").data())
