#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x "$ROOT_DIR/.venv310/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv310/bin/python"
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

DATASET_DIR="src/textgraphx/datastore/dataset_eval_batch"
GOLD_DIR="src/textgraphx/datastore/annotated"
OUT_DIR="src/textgraphx/datastore/evaluation/baseline"
mkdir -p "$OUT_DIR"

echo "=== INITIALIZING BATCH BASELINE EVLAUATION ==="
$PYTHON -m textgraphx.run_pipeline \
  --dataset "$DATASET_DIR" \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment,tlinks

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir "$GOLD_DIR" \
  --out-json "$OUT_DIR/eval_batch_baseline.json" \
  --out-markdown "$OUT_DIR/eval_batch_baseline.md" \
  --export-csv-prefix "$OUT_DIR/eval_batch_baseline" \
  --pred-neo4j

