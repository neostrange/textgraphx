from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
query = "MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence) WHERE d.id = 112579 AND tok.tok_index_doc >= 15 AND tok.tok_index_doc <= 35 RETURN tok.tok_index_doc as idx, tok.text as text, tok.pos as pos, tok.dep as dep, tok.headTokenIndex as head_idx ORDER BY idx"
res = graph.run(query).data()
print("--- Tokens 15-35 ---")
for r in res: print(r)
query2 = "MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence) WHERE d.id = 112579 AND tok.tok_index_doc >= 100 AND tok.tok_index_doc <= 110 RETURN tok.tok_index_doc as idx, tok.text as text, tok.pos as pos, tok.dep as dep, tok.headTokenIndex as head_idx ORDER BY idx"
res2 = graph.run(query2).data()
print("--- Tokens 100-110 ---")
for r in res2: print(r)
