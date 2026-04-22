import json, glob
files = sorted(glob.glob('textgraphx/datastore/evaluation/cycle_*/eval_report_strict.json'), reverse=True)
data = json.load(open(files[0]))
for doc in data['diagnostics']['documents']:
    if str(doc.get('doc_id')) == '76437':
        events = doc.get("event", {})
        print("True Positives:", len(events.get("true_positives", [])))
        for tp in events.get("true_positives", []):
            if 'drag' in str(tp).lower():
                print("Found in TP:", tp)
