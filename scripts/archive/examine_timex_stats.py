import json
import glob
import os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
for r in report['reports']:
    counts = r['strict']['timex'].get('counts', {})
    print(f"Doc: {r['doc_id']} Counts: {counts}")
