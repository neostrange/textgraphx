from textgraphx.db import GraphDB
graph = GraphDB("bolt://localhost:7687", "neo4j", "password!123")
with graph.get_session() as session:
    res = session.run("MATCH (a:AnnotatedText) RETURN a.id LIMIT 5")
    print(res.data())
