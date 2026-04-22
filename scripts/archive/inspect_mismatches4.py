import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Let's look inside Reports:")
for r in data.get('reports', [])[:1]:
    print("Keys in report:", list(r.keys()))
    if 'metrics' in r:
        print("Metrics keys:", list(r['metrics'].keys()))
    if 'diagnostics' in r:
         print("Diagnostics keys:", list(r['diagnostics'].keys()))
         if 'entity' in r['diagnostics']:
             print("Entity Diagnostics:", r['diagnostics']['entity'])

print("\nWhere are the false positives/negatives stored?")
if 'diagnostics' in r and 'layer_issues' in r['diagnostics']:
    print("Layer issues:", r['diagnostics']['layer_issues'])

import csv
csv_path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict_docs.csv'
import pandas as pd
try:
    df = pd.read_csv(csv_path)
    print("CSV Columns:", df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head(2))
except Exception as e:
    print(f"Failed to read CSV: {e}")

