from textgraphx.neo4j_client import make_graph_from_config
g = make_graph_from_config()
q = """
MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)-[:HAS_TOKEN]->(app_root:TagOccurrence)-[:IS_DEPENDENT {type: "appos"}]->(head:TagOccurrence)
MATCH (d)-[:CONTAINS_SENTENCE]->(s)-[:HAS_TOKEN]->(desc:TagOccurrence)-[:IS_DEPENDENT*0..]->(app_root)
WITH d, head, app_root, min(desc.tok_index_doc) AS start_tok, max(desc.tok_index_doc) AS end_tok
RETURN d.id as doc_id, head.text as head_text, app_root.text as appos_head, start_tok, end_tok
ORDER BY start_tok LIMIT 10
"""
for r in g.run(q).data(): print(r)
