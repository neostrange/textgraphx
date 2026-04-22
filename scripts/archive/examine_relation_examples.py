import json
with open('single_eval.json') as f:
    d = json.load(f)
r = d['reports'][0]['strict'].get('relation', {}).get('examples', {})
print("SPURIOUS:")
for ex in r.get('spurious', [])[:3]:
    print(ex)
print("\nMISSING:")
for ex in r.get('missing', [])[:3]:
    print(ex)
