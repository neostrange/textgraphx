#!/usr/bin/env bash
set -euo pipefail

cd /home/neo/environments/textgraphx
PYTHON=".venv310/bin/python"

echo "=== INITIALIZING BATCH BASELINE EVLAUATION ==="
$PYTHON -m textgraphx.run_pipeline \
  --dataset textgraphx/datastore/dataset_eval_batch \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment,tlinks

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir textgraphx/datastore/annotated \
  --out-json textgraphx/datastore/evaluation/eval_batch_baseline.json \
  --pred-neo4j

