import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Let's map tokens to actual words using the NAF or just querying Neo4j if possible. Actually, let's just use spaCy real quick to guess.")
