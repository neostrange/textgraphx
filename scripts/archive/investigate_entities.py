import json

def process():
    with open("textgraphx/datastore/evaluation/eval_batch_baseline_examples.json") as f: 
        d1 = json.load(f)
    print("========== ENTITY FALSE NEGATIVES (MISSING) ==========")
    fp_examples = d1.get("reports", [])[0].get("strict", {}).get("entity", {}).get("examples", {}).get("missing", [])
    for x in fp_examples[:15]:
        print(f" - {x.get('text')} (class: {x.get('ent_class')} | h_pos: {x.get('head_pos')} | synt_type: {x.get('syntactic_type')})")

    print("\n========== ENTITY FALSE POSITIVES (SPURIOUS) ==========")
    fp_examples = d1.get("reports", [])[0].get("strict", {}).get("entity", {}).get("examples", {}).get("spurious", [])
    for x in fp_examples[:15]:
        print(f" - {x.get('text')} (class: {x.get('ent_class')} | h_pos: {x.get('head_pos')} | synt_type: {x.get('syntactic_type')})")
        
    print("\n========== EVENT FALSE NEGATIVES (MISSING) ==========")
    fp_examples = d1.get("reports", [])[0].get("strict", {}).get("event", {}).get("examples", {}).get("missing", [])
    for x in fp_examples[:15]:
        print(f" - {x.get('text')} (class: {x.get('class')} | rel: {x.get('relType')})")
        
    print("\n========== EVENT FALSE POSITIVES (SPURIOUS) ==========")
    fp_examples = d1.get("reports", [])[0].get("strict", {}).get("event", {}).get("examples", {}).get("spurious", [])
    for x in fp_examples[:15]:
        print(f" - {x.get('text')} (class: {x.get('class')} | rel: {x.get('relType')})")
        
process()
