from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
res = graph.run("MATCH (m:DiscourseEntity)-[:IN_MENTION|PARTICIPATES_IN]-(tok)-[:HAS_TOKEN]-(s)-[:CONTAINS_SENTENCE]-(d:AnnotatedText) RETURN d.id as doc_id, count(DISTINCT m) as cnt ORDER BY d.id").data()
for r in res: print(r)
