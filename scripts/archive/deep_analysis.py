import json, glob
files = sorted(glob.glob('textgraphx/datastore/evaluation/cycle_20*/eval_report_strict.json'), reverse=True)
data = json.load(open(files[0]))

fps = []
for d in data['diagnostics']['documents']:
    for l in d['layers']:
        if l['layer'] == 'relation':
            for ex in l.get('examples', {}).get('spurious', []):
                rel_type = ex['predicted'].get('rel_type', 'UNKNOWN')
                source = ex['predicted'].get('source', {}).get('text', 'UNKNOWN')
                target = ex['predicted'].get('target', {}).get('text', 'UNKNOWN')
                fps.append(f"{rel_type}: {source} -> {target}")

from collections import Counter
c = Counter(fps)
print("Top Spurious Relations:")
for rel, count in c.most_common(20):
    print(f"{count}x | {rel}")
