from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (tok:TagOccurrence) WHERE tok.text STARTS WITH 'drag' RETURN tok.pos, tok.upos, tok.tok_index_doc, tok.text").data()
print(res)

res2 = graph.run("MATCH (tok:TagOccurrence)-[r:IS_DEPENDENT]->(mod) WHERE tok.text STARTS WITH 'drag' RETURN tok.text, type(r), r.type, mod.text, mod.pos, mod.tok_index_doc").data()
print(res2)
