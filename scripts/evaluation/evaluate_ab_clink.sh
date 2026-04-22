#!/usr/bin/env bash
set -euo pipefail

cd /home/neo/environments/textgraphx
PYTHON=".venv310/bin/python"

echo "=== PASS 1: OFF ==="
$PYTHON -m textgraphx.run_pipeline \
  --dataset textgraphx/datastore/dataset_eval_single \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment,tlinks

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir textgraphx/datastore/annotated \
  --out-json textgraphx/datastore/evaluation/ab_off.json \
  --pred-neo4j

echo "=== PASS 2: ON ==="
# We only need to run TLinks with ON instead of repeating the whole pipeline because TLinks phase is mostly idempotent / overwritable!
# Wait, tlinks phase doesn't clear old tlinks? Actually, the pipeline might clear them. Let's just run from scratch to be totally safe.

cat << 'PY_EOF' > run_ab_on.py
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
  --dataset textgraphx/datastore/dataset_eval_single \
  --cleanup full \
  --phases ingestion,refinement,temporal,event_enrichment

$PYTHON run_ab_on.py

$PYTHON -m textgraphx.tools.evaluate_meantime \
  --gold-dir textgraphx/datastore/annotated \
  --out-json textgraphx/datastore/evaluation/ab_on.json \
  --pred-neo4j
