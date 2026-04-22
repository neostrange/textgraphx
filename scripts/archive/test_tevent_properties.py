from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (e:TEvent) RETURN keys(e), e.doc_id, e.id LIMIT 3").data()
for r in res:
    print(r)
