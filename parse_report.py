import json
import glob

files = glob.glob("textgraphx/datastore/evaluation/*/eval_report_strict.json")
files.sort()
last_file = files[-1]

with open(last_file) as f:
    rep = json.load(f)

for doc_res in rep["reports"]:
    strict = doc_res.get("strict", {})
    if "relation" not in strict: continue
    rels = strict["relation"]
    print(f"DOC {doc_res.get('doc_id', '?')} FN: {rels.get('examples', {}).get('missing', 0)}")
