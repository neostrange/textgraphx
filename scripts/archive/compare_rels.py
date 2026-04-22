import json

try:
    with open('textgraphx/datastore/evaluation/cycle_temp/eval_report_strict.json', 'r') as f:
        data = json.load(f)
        
    for doc in data.get('documents', [])[:2]:
        print(f"DOC: {doc['doc_id']}")
        rel_layer = next((l for l in doc.get('layers', []) if l['layer'] == 'relation'), None)
        if rel_layer and 'examples' in rel_layer:
            for bucket, ex_list in rel_layer['examples'].items():
                if ex_list:
                    print(f"  {bucket}:")
                    for ex in ex_list[:5]:
                        print(f"    - {ex}")
except Exception as e:
    print(e)
