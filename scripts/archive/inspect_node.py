from textgraphx.neo4j_client import make_graph_from_config
from pprint import pprint
client = make_graph_from_config()

q = "MATCH (m:EventMention)-[:REFERS_TO]->(evt:TEvent) RETURN count(m)"
res = client.run(q).data()
print("EventMention -> TEvent REFERS_TO:", res)

q2 = "MATCH (m:EventMention:TEvent) RETURN count(m)"
res2 = client.run(q2).data()
print("EventMention IS TEvent:", res2)

q3 = """
MATCH (src)-[r:EVENT_PARTICIPANT]->(evt:TEvent)
RETURN labels(evt), count(evt)
LIMIT 10
"""
res3 = client.run(q3).data()
print("TEvent from PARTICIPANT is labeled:", res3)
