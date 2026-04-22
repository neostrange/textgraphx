import os
import json
import glob

latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)

for r in report['reports']:
    counts = r['strict']['relation'].get('counts', {})
    false_negatives = len(r['strict']['relation']['examples'].get('false_negatives', []))
    false_positives = len(r['strict']['relation']['examples'].get('false_positives', []))
    print(f"Doc {r['doc_id']}: counts {counts}, FN={false_negatives}, FP={false_positives}")

    # let's look at the first FN
    fns = r['strict']['relation']['examples'].get('false_negatives', [])
    fps = r['strict']['relation']['examples'].get('false_positives', [])
    if fns:
        print("  Sample FN:")
        for fn in fns[:2]:
            print(f"   {fn}")
    if fps:
        print("  Sample FP:")
        for fp in fps[:2]:
            print(f"   {fp}")

