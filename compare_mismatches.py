import json

with open('textgraphx/datastore/evaluation/cycle_20260410T091513Z/eval_report_strict.json') as f:
    eval_json_old = json.load(f)
    
old_mm = []
for doc in eval_json_old['diagnostics']['documents']:
    for doc_layer in doc.get('layers', []):
        if doc_layer['layer'] == 'event':
            for mm in doc_layer.get('examples', {}).get('boundary_mismatch', []):
                old_mm.append(f"{mm['gold']['attrs'].get('pred')} {mm['gold']['span']} -> {mm['predicted']['span']}")

import glob
latest_dir = sorted(glob.glob('textgraphx/datastore/evaluation/cycle_*'))[-1]
with open(latest_dir + '/eval_report_strict.json') as f:
    eval_json_new = json.load(f)

new_mm = []
for doc in eval_json_new['diagnostics']['documents']:
    for doc_layer in doc.get('layers', []):
        if doc_layer['layer'] == 'event':
            for mm in doc_layer.get('examples', {}).get('boundary_mismatch', []):
                new_mm.append(f"{mm['gold']['attrs'].get('pred')} {mm['gold']['span']} -> {mm['predicted']['span']}")

print("NEW MISMATCHES NOT IN OLD:")
for mm in set(new_mm) - set(old_mm):
    print(mm)

print("\nOLD MISMATCHES FIXED IN NEW:")
for mm in set(old_mm) - set(new_mm):
    print(mm)
