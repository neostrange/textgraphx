from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = """
MATCH (tok:TagOccurrence)-[r]->(e:TEvent)
RETURN type(r) AS rel_type, count(*) AS c
"""
print("Out of TOK to TEvent:", graph.run(q).data())

q2 = """
MATCH (e:TEvent)-[r]->(tok:TagOccurrence)
RETURN type(r) AS rel_type, count(*) AS c
"""
print("Out of TEvent to TOK:", graph.run(q2).data())

q3 = """
MATCH (tok:TagOccurrence)-[r]-(e:TEvent)
RETURN type(r) AS rel_type, count(*) AS c
"""
print("Any direction TOK to TEvent:", graph.run(q3).data())

q4 = """
MATCH (at:AnnotatedText {id: '61327'})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok)
MATCH (tok)-[r]-(e:TEvent)
RETURN type(r), count(r)
"""
print("61327 TEvent token connects:", graph.run(q4).data())
