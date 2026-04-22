import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = ROOT / "src" / "textgraphx" / "datastore" / "evaluation" / "baseline" / "eval_batch_baseline_examples.json"

def process():
    with BASELINE_FILE.open() as f:
        d1 = json.load(f)
    print("========== EVENT FALSE NEGATIVES (MISSING) ==========")
    for report in d1.get("reports", [])[:1]:
        fp_examples = report.get("strict", {}).get("event", {}).get("examples", {}).get("missing", [])
        for x in fp_examples[:40]:
            attrs = x.get('gold', {}).get('attrs', {})
            print(f" - {attrs.get('pred', 'N/A')} (pos: {attrs.get('pos', 'N/A')} | tense: {attrs.get('tense', 'N/A')})")

process()
