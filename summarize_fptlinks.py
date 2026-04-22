import json
d = json.load(open('eval_report_strict.json'))
print("Spurious (FP) Relations Sample:")
for doc in d['reports']:
   spurious = doc['relaxed']['relation']['examples'].get('spurious', [])
   if spurious:
      for r in spurious[:10]:
         print(f"FP: {r}")
      break
