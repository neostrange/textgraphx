import json, glob, os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f: report = json.load(f)
r = report['reports'][0]
print(r['doc_id'])
for item in r['strict']['event']['examples'].get('missing', []):
    if item['gold']['span'] == [87] or item['gold']['span'] == [67] or item['gold']['span'] == [36]:
        print(f"Missing: {item}")
for item in r['strict']['event']['examples'].get('matched_pairs', []):
    if item['gold']['span'] == [87] or item['gold']['span'] == [67] or item['gold']['span'] == [36]:
        print(f"Matched: {item}")
