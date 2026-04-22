import json

with open("textgraphx/datastore/evaluation/eval_batch_baseline.json", "r") as f:
    report = json.load(f)

rel_dict = report['aggregate']['strict']['has_participant']
print("Overall HAS_PARTICIPANT Strict:")
print("FN:", rel_dict['fn'], "FP:", rel_dict['fp'], "TP:", rel_dict['tp'])
