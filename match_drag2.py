from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (em:EventMention) RETURN em.pred, em.form, em.start_tok, em.end_tok LIMIT 100").data()
import json
for r in res:
    if 'drag' in str(r).lower() or 'tumble' in str(r).lower():
        print(r)
