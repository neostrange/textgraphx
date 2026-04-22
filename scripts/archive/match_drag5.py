from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
query = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'VB' AND trig_tok.text = 'dragged'
        MATCH (trig_tok)-[dep:IS_DEPENDENT]->(prt:TagOccurrence)
        WHERE dep.type IN ['prt', 'acomp']
        RETURN em.id, trig_tok.text, prt.text, prt.tok_index_doc, em.start_tok, em.end_tok
"""
res = graph.run(query).data()
print(res)
