import json
with open('textgraphx/datastore/evaluation/cycle_temp/eval_report_strict.json') as f:
    d = json.load(f)
for doc in d.get("detail", []):
    print("DOC", doc.get("doc_id"))
    for lr in doc.get("layers", []):
        if lr.get("layer") == "relation":
            for bucket, ex_list in lr.get("examples", {}).items():
                if ex_list:
                    print(f"  {bucket}:")
                    for ex in ex_list[:3]:
                        print(f"    - {ex}")
