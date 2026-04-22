import json

with open('eval_report_strict.json', 'r') as f:
    report = json.load(f)

entities = []
events = []

def extract(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'entity' and isinstance(v, dict) and 'spurious' in v and isinstance(v['spurious'], list):
                entities.extend(v['spurious'])
            elif k == 'event' and isinstance(v, dict) and 'spurious' in v and isinstance(v['spurious'], list):
                events.extend(v['spurious'])
            else:
                extract(v)
    elif isinstance(obj, list):
        for item in obj:
            extract(item)

extract(report)

print("Spurious Entities:")
for e in entities[:10]: print(" - " + str(e))
print("\nSpurious Events:")
for e in events[:10]: print(" - " + str(e))
