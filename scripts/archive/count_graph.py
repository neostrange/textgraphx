from py2neo import Graph
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password!123"))
r1 = graph.run("MATCH ()-[r:EVENT_PARTICIPANT]->() RETURN count(r) AS c").data()
print("EVENT_PARTICIPANT:", r1[0]['c'])
r2 = graph.run("MATCH ()-[r:TLINK]->() RETURN count(r) AS c").data()
print("TLINK:", r2[0]['c'])
