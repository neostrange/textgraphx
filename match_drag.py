from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent) WHERE em.form STARTS WITH 'drag' RETURN em.pred, em.form, em.start_tok, em.end_tok, em.token_start, em.token_end").data()
for r in res:
    print(r)
