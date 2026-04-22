import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = ROOT / "src" / "textgraphx" / "datastore" / "evaluation" / "baseline" / "eval_batch_baseline.json"

with BASELINE_FILE.open("r") as f:
    report = json.load(f)

rel_dict = report['aggregate']['strict']['has_participant']
print("Overall HAS_PARTICIPANT Strict:")
print("FN:", rel_dict['fn'], "FP:", rel_dict['fp'], "TP:", rel_dict['tp'])
