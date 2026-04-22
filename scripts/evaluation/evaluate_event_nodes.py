from textgraphx.neo4j_client import make_graph_from_config

g = make_graph_from_config()
res = g.run("MATCH (e:TEvent {doc_id: 96770}) OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(e) RETURN e.pred, e.form, e.start_char, e.end_char, count(tok) AS trigger_count LIMIT 20").data()

for r in res:
    print(r)
