import json
with open('textgraphx/datastore/evaluation/cycle_20260410T091513Z/eval_report_strict.json') as f:
    eval_json = json.load(f)

for doc in eval_json['diagnostics']['documents']:
    for doc_layer in doc.get('layers', []):
        if doc_layer['layer'] == 'event':
            b_mismatches = doc_layer.get('examples', {}).get('boundary_mismatch', [])
            for mm in b_mismatches[:5]:
                print(f"GOLD: {mm['gold']}")
                print(f"PRED: {mm['predicted']}\n")
