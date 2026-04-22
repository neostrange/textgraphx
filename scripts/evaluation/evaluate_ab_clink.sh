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

DATASET_DIR="src/textgraphx/datastore/dataset_eval_single"
GOLD_DIR="src/textgraphx/datastore/annotated"
OUT_DIR="src/textgraphx/datastore/evaluation/latest"
mkdir -p "$OUT_DIR"

echo "=== PASS 1: OFF ==="
$PYTHON -m textgraphx.run_pipeline \
  --dataset "$DATASET_DIR" \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment,tlinks

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir "$GOLD_DIR" \
  --out-json "$OUT_DIR/ab_off.json" \
  --out-markdown "$OUT_DIR/ab_off.md" \
  --export-csv-prefix "$OUT_DIR/ab_off" \
  --pred-neo4j

echo "=== PASS 2: ON ==="

TMP_RUN="$(mktemp "$ROOT_DIR/.tmp_run_ab_on.XXXXXX.py")"
trap 'rm -f "$TMP_RUN"' EXIT

cat << 'PY_EOF' > "$TMP_RUN"
from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.phase_wrappers import TlinksRecognizerWrapper

cfg = get_config()
cfg.runtime.enable_tlink_xml_seed = True

g = make_graph_from_config()
w = TlinksRecognizerWrapper(g)
w.execute()
PY_EOF

$PYTHON -m textgraphx.run_pipeline \
  --dataset "$DATASET_DIR" \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment

$PYTHON "$TMP_RUN"

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir "$GOLD_DIR" \
  --out-json "$OUT_DIR/ab_on.json" \
  --out-markdown "$OUT_DIR/ab_on.md" \
  --export-csv-prefix "$OUT_DIR/ab_on" \
  --pred-neo4j
