import json

with open('textgraphx/datastore/evaluation/cycle_20260410T091513Z/eval_report_strict.json') as f:
    eval_json = json.load(f)

for doc in eval_json['diagnostics']['documents']:
    for doc_layer in doc.get('layers', []):
        if doc_layer['layer'] == 'event':
            for k in doc_layer.get('examples', {}):
                for mm in doc_layer['examples'][k][:10]:
                    if 'drag' in str(mm).lower():
                        print(f"{k}: GOLD {mm['gold']} \nPRED {mm['predicted']}\n")
