from textgraphx.config import get_config
from neo4j import GraphDatabase

cfg = get_config()
driver = GraphDatabase.driver(cfg.neo4j.uri, auth=(cfg.neo4j.user, cfg.neo4j.password))

with driver.session() as session:
    res = session.run("MATCH (n:TEvent)-[:TRIGGERS]-(t:TagOccurrence)-[:HAS_TOKEN]-(:Sentence)-[:CONTAINS_SENTENCE]-(d:AnnotatedText) RETURN t.text as head, n.class as class, count(n) as c ORDER BY c DESC LIMIT 20")
    print("\nTop extracted events by Neo4j:")
    for r in res:
        print(f" - {r['head']} ({r['class']})")
        
