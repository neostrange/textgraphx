import json
with open('single_eval.json') as f:
    data = json.load(f)
print("TLINK / RELATION F1 score:")
print(data.get('aggregate', {}).get('micro', {}).get('strict', {}).get('relation'))
