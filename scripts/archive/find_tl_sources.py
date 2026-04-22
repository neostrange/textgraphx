import json
d = json.load(open('eval_report_strict.json'))
sources = set()
for rel in d['reports'][0].get("relations", []):
   print(rel)
