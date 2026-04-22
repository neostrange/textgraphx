from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (em:EventMention {id: 'ei1_mention'}) RETURN em.doc_id, em.low_confidence, em.start_tok, em.end_tok").data()
print("EventMention:", res)
