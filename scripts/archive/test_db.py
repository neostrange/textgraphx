from neo4j import GraphDatabase
d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "textgraph"))
with d.session() as s:
    r = s.run("MATCH (a)-[r:EVENT_PARTICIPANT]->(b) RETURN properties(r) LIMIT 5").data()
    print("PROPS:", r)
