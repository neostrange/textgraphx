with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    evaluator_content = f.read()

target = """            WHERE r.is_core = true OR r.is_core IS NULL
            WHERE r.is_core = true OR r.is_core IS NULL
            WHERE evt.doc_id = doc_id"""
replacement = """            WHERE (r.is_core = true OR r.is_core IS NULL)
              AND (evt.doc_id = doc_id"""

if target in evaluator_content:
    evaluator_content = evaluator_content.replace(target, replacement)
    evaluator_content = evaluator_content.replace("""               OR EXISTS {
                   MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(evt)
               }""", """               OR EXISTS {
                   MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(evt)
               })""")
    with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
        f.write(evaluator_content)
    print("Fixed EVENT_PARTICIPANT query")
else:
    print("Could not find EVENT_PARTICIPANT target")
