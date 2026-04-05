#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -x "$ROOT_DIR/.venv310/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv310/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

DATASET_DIR="${1:-$ROOT_DIR/textgraphx/datastore/dataset}"
GOLD_DIR="${2:-$ROOT_DIR/textgraphx/datastore/annotated}"
RUN_TAG="${3:-cycle_$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_DIR="$ROOT_DIR/textgraphx/datastore/evaluation/$RUN_TAG"

mkdir -p "$OUT_DIR"

export TEXTGRAPHX_RUNTIME_MODE="testing"
export TEXTGRAPHX_STRICT_TRANSITION_GATE="true"
export TEXTGRAPHX_NAF_SENTENCE_MODE="meantime"

cat <<EOF
=== TextGraphX MEANTIME Evaluation Cycle ===
Python:        $PYTHON_BIN
Dataset:       $DATASET_DIR
Gold:          $GOLD_DIR
Run tag:       $RUN_TAG
Output dir:    $OUT_DIR
Runtime mode:  $TEXTGRAPHX_RUNTIME_MODE
Strict gate:   $TEXTGRAPHX_STRICT_TRANSITION_GATE
NAF mode:      $TEXTGRAPHX_NAF_SENTENCE_MODE
EOF

echo "[1/5] Preflight health check"
"$PYTHON_BIN" "$ROOT_DIR/textgraphx/run_pipeline.py" --check

echo "[2/5] Full Neo4j cleanup"
"$PYTHON_BIN" - <<'PY'
from textgraphx.neo4j_client import make_graph_from_config

graph = make_graph_from_config()
rows = graph.run("MATCH (n) DETACH DELETE n RETURN count(n) AS c").data()
deleted = rows[0].get("c", 0) if rows else 0
print(f"Deleted nodes: {deleted}")
if hasattr(graph, "close"):
    graph.close()
PY

echo "[3/5] Full pipeline run"
PIPELINE_OK=1
if ! "$PYTHON_BIN" "$ROOT_DIR/textgraphx/run_pipeline.py" \
  --dataset "$DATASET_DIR" \
  --cleanup none \
  --phases ingestion,refinement,temporal,event_enrichment,tlinks; then
  PIPELINE_OK=0
fi

if [[ "$PIPELINE_OK" -ne 1 ]]; then
  echo "Pipeline failed under strict gate. Capturing baseline with strict gate disabled."
  export TEXTGRAPHX_STRICT_TRANSITION_GATE="false"

  echo "[3a/5] Re-clean Neo4j for fallback baseline run"
  "$PYTHON_BIN" - <<'PY'
from textgraphx.neo4j_client import make_graph_from_config

graph = make_graph_from_config()
rows = graph.run("MATCH (n) DETACH DELETE n RETURN count(n) AS c").data()
deleted = rows[0].get("c", 0) if rows else 0
print(f"Deleted nodes: {deleted}")
if hasattr(graph, "close"):
    graph.close()
PY

  echo "[3b/5] Full pipeline run (fallback non-strict baseline)"
  "$PYTHON_BIN" "$ROOT_DIR/textgraphx/run_pipeline.py" \
    --dataset "$DATASET_DIR" \
    --cleanup none \
    --phases ingestion,refinement,temporal,event_enrichment,tlinks
fi

echo "[4/5] Evaluate strict diagnostics mode"
"$PYTHON_BIN" -m textgraphx.tools.evaluate_meantime \
  --gold-dir "$GOLD_DIR" \
  --pred-neo4j \
  --analysis-mode strict \
  --f1-threshold 0.75 \
  --max-examples 10 \
  --out-json "$OUT_DIR/eval_report_strict.json" \
  --out-markdown "$OUT_DIR/eval_report_strict.md" \
  --export-csv-prefix "$OUT_DIR/eval_report_strict" >/dev/null

echo "[5/5] Evaluate relaxed diagnostics mode"
"$PYTHON_BIN" -m textgraphx.tools.evaluate_meantime \
  --gold-dir "$GOLD_DIR" \
  --pred-neo4j \
  --analysis-mode relaxed \
  --f1-threshold 0.75 \
  --max-examples 10 \
  --out-json "$OUT_DIR/eval_report_relaxed.json" \
  --out-markdown "$OUT_DIR/eval_report_relaxed.md" \
  --export-csv-prefix "$OUT_DIR/eval_report_relaxed" >/dev/null

echo "[6/6] Build concise baseline summary"
"$PYTHON_BIN" - <<PY
import json
from pathlib import Path

out_dir = Path(r"$OUT_DIR")
strict = json.loads((out_dir / "eval_report_strict.json").read_text(encoding="utf-8"))

micro = strict.get("aggregate", {}).get("micro", {})
strict_micro = micro.get("strict", {})
relaxed_micro = micro.get("relaxed", {})
scorecards = strict.get("scorecards", {})
tm = scorecards.get("time_ml_compliance", {})
bt = scorecards.get("beyond_timeml_reasoning", {})
suggestions = strict.get("diagnostics", {}).get("suggestions", [])

lines = []
lines.append("# Cycle Summary")
lines.append("")
lines.append(f"- Documents evaluated: {strict.get('documents_evaluated', 0)}")
lines.append("")
lines.append("## Micro F1")
for layer in ("entity", "event", "timex", "relation"):
    sf1 = float(strict_micro.get(layer, {}).get("f1", 0.0))
    rf1 = float(relaxed_micro.get(layer, {}).get("f1", 0.0))
    lines.append(f"- {layer}: strict={sf1:.4f}, relaxed={rf1:.4f}")
lines.append("")
lines.append("## Scorecards")
lines.append(f"- TimeML compliance composite: {float(tm.get('composite', 0.0)):.4f}")
lines.append(f"- Beyond-TimeML reasoning composite: {float(bt.get('composite', 0.0)):.4f}")
lines.append("")
lines.append("## Top Suggestions")
if suggestions:
    for s in suggestions[:10]:
        lines.append(f"- {s}")
else:
    lines.append("- none")

(out_dir / "cycle_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print((out_dir / "cycle_summary.md").as_posix())
PY

echo "Cycle complete. Artifacts: $OUT_DIR"
