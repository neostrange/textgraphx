import json

d = json.load(open("eval_report_strict.json"))
for doc in d["reports"]:
    d_id = doc["doc_id"]
    relaxed_rels = doc["relaxed"]["relation"]
    fp_rels = relaxed_rels.get("false_positives", [])
    if fp_rels:
        print(f"--- Doc {d_id} False Positive Relations (First 10) ---")
        for i, fp in enumerate(fp_rels[:10]):
           print(f"FP {i}: {fp['kind']} - src={fp.get('source_id')} -> tgt={fp.get('target_id')} attrs={fp.get('attributes')}")
