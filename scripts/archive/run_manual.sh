export PYTHON_BIN="./.venv310/bin/python"
export OUT_DIR="textgraphx/datastore/evaluation/cycle_temp"
mkdir -p "$OUT_DIR"
$PYTHON_BIN -m textgraphx.tools.evaluate_meantime \
  --pred-neo4j \
  --gold-dir textgraphx/datastore/annotated \
  --analysis-mode strict \
  --normalize-nominal-boundaries \
  --nominal-precision-filters \
  --gold-like-nominal-filter \
  --f1-threshold 0.75 \
  --max-examples 10 \
  --out-json "$OUT_DIR/eval_report_strict.json" \
  --out-markdown "$OUT_DIR/eval_report_strict.md" \
  --export-csv-prefix "$OUT_DIR/eval_report_strict" 2> eval_stderr_bypass_error.log
