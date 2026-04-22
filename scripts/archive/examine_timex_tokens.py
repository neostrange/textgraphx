import json
import glob
import os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
for r in report['reports']:
    dt = {int(t[0]): t[1] for t in r['gold_documents'][r['doc_id']]['tokens']}
    bms = r['strict']['timex']['examples'].get('boundary_mismatch', [])
    for bm in bms:
        p = bm['predicted']['span']
        g = bm['gold']['span']
        print(f"Doc: {r['doc_id']} Pred: {[dt.get(i) for i in p]} Gold: {[dt.get(i) for i in g]}")
