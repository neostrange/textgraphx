import json
import glob
import os

latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)

for r in report['reports']:
    doc_id = r['doc_id']
    strict = r['strict']['entity']['examples']
    
    missing = strict.get('missing', [])
    spurious = strict.get('spurious', [])
    
    if not missing and not spurious: continue
    
    print(f"\n--- DOC {doc_id} ---")
    if missing:
        print("MISSING:")
        for m in missing[:5]:
            span = m.get('gold', {}).get('span', [])
            typ = m.get('gold', {}).get('attrs', {}).get('syntactic_type', '')
            print("  ", span, typ)
            
    if spurious:
        print("SPURIOUS:")
        for s in spurious[:5]:
            span = s.get('predicted', {}).get('span', [])
            typ = s.get('predicted', {}).get('attrs', {}).get('syntactic_type', '')
            print("  ", span, typ)
