from textgraphx.config import get_config
from neo4j import GraphDatabase
cfg = get_config()
driver = GraphDatabase.driver(cfg.neo4j.uri, auth=(cfg.neo4j.user, cfg.neo4j.password))
with driver.session() as session:
    res = session.run("MATCH (n:AnnotatedText) RETURN count(n) AS c").single()
    print("AnnotatedText:", res['c'])
    res = session.run("MATCH (n:Document) RETURN count(n) AS c").single()
    print("Document:", res['c'])
