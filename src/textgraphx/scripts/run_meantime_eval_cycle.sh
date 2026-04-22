#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TOTAL_STEPS=7
LEGACY_RELATION_SCOPE="${LEGACY_RELATION_SCOPE:-tlink}"
FULL_RELATION_SCOPE="${FULL_RELATION_SCOPE:-tlink,has_participant}"

if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
	PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [[ -x "$ROOT_DIR/.venv310/bin/python" ]]; then
	PYTHON_BIN="$ROOT_DIR/.venv310/bin/python"
elif [[ -x "$ROOT_DIR/../.venv310/bin/python" ]]; then
	PYTHON_BIN="$ROOT_DIR/../.venv310/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
	PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/../.venv/bin/python" ]]; then
	PYTHON_BIN="$ROOT_DIR/../.venv/bin/python"
else
	PYTHON_BIN="python3"
fi

resolve_dir() {
	local candidate="$1"
	if [[ -d "$candidate" ]]; then
		printf '%s\n' "$candidate"
		return 0
	fi
	if [[ -d "$ROOT_DIR/$candidate" ]]; then
		printf '%s\n' "$ROOT_DIR/$candidate"
		return 0
	fi
	if [[ -d "$ROOT_DIR/../$candidate" ]]; then
		printf '%s\n' "$ROOT_DIR/../$candidate"
		return 0
	fi
	printf '%s\n' "$candidate"
}

DATASET_DIR="$(resolve_dir "${1:-$ROOT_DIR/datastore/dataset}")"
GOLD_DIR="$(resolve_dir "${2:-$ROOT_DIR/datastore/annotated}")"
RUN_TAG="${3:-latest}"
OUT_DIR="$ROOT_DIR/datastore/evaluation/$RUN_TAG"

if [[ "$RUN_TAG" == "latest" ]]; then
	mkdir -p "$OUT_DIR"
	find "$OUT_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
elif [[ -e "$OUT_DIR" ]] && [[ -n "$(find "$OUT_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
	echo "[ERROR] Output dir already exists and is not empty: $OUT_DIR" >&2
	echo "[ERROR] Provide a unique run tag as argument 3." >&2
	exit 1
fi

mkdir -p "$OUT_DIR"

require_dir() {
	local label="$1"
	local path="$2"
	if [[ ! -d "$path" ]]; then
		echo "[ERROR] $label directory not found: $path" >&2
		exit 1
	fi
}

cleanup_neo4j() {
	"$PYTHON_BIN" - <<'PY'
from textgraphx.neo4j_client import make_graph_from_config

graph = make_graph_from_config()
rows = graph.run("MATCH (n) DETACH DELETE n RETURN count(n) AS c").data()
deleted = rows[0].get("c", 0) if rows else 0
print(f"Deleted nodes: {deleted}")
if hasattr(graph, "close"):
		graph.close()
PY
}

export TEXTGRAPHX_RUNTIME_MODE="testing"
export TEXTGRAPHX_STRICT_TRANSITION_GATE="true"
export TEXTGRAPHX_NAF_SENTENCE_MODE="meantime"
export TEXTGRAPHX_ENABLE_TLINK_XML_SEED="true"

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
TLINK seed:    $TEXTGRAPHX_ENABLE_TLINK_XML_SEED
EOF

echo "[1/$TOTAL_STEPS] Validate input directories"
require_dir "Dataset" "$DATASET_DIR"
require_dir "Gold" "$GOLD_DIR"

echo "[2/$TOTAL_STEPS] Preflight health check"
"$PYTHON_BIN" -m textgraphx.run_pipeline --check

echo "[3/$TOTAL_STEPS] Full Neo4j cleanup"
cleanup_neo4j

echo "[4/$TOTAL_STEPS] Full pipeline run"
PIPELINE_OK=1
FALLBACK_USED=false
if ! "$PYTHON_BIN" -m textgraphx.run_pipeline \
	--dataset "$DATASET_DIR" \
	--cleanup none \
	--phases ingestion,refinement,temporal,event_enrichment,tlinks; then
	PIPELINE_OK=0
fi

if [[ "$PIPELINE_OK" -ne 1 ]]; then
	echo "Pipeline failed under strict gate. Capturing baseline with strict gate disabled."
	export TEXTGRAPHX_STRICT_TRANSITION_GATE="false"
	FALLBACK_USED=true

	echo "[4a/$TOTAL_STEPS] Re-clean Neo4j for fallback baseline run"
	cleanup_neo4j

	echo "[4b/$TOTAL_STEPS] Full pipeline run (fallback non-strict baseline)"
	"$PYTHON_BIN" -m textgraphx.run_pipeline \
		--dataset "$DATASET_DIR" \
		--cleanup none \
		--phases ingestion,refinement,temporal,event_enrichment,tlinks
fi

run_eval_mode() {
	local mode="$1"
	local relation_scope="$2"
	local stem="$3"
	"$PYTHON_BIN" -m textgraphx.tools.evaluate_meantime \
		--gold-dir "$GOLD_DIR" \
		--pred-neo4j \
		--analysis-mode "$mode" \
		--normalize-nominal-boundaries \
		--nominal-precision-filters \
		--gold-like-nominal-filter \
		--relation-scope "$relation_scope" \
		--f1-threshold 0.75 \
		--max-examples 10 \
		--out-json "$OUT_DIR/${stem}.json" \
		--out-markdown "$OUT_DIR/${stem}.md" \
		--export-csv-prefix "$OUT_DIR/${stem}" >/dev/null
}

echo "[5/$TOTAL_STEPS] Evaluate diagnostics mode (legacy scope: $LEGACY_RELATION_SCOPE)"
for mode in strict relaxed; do
	run_eval_mode "$mode" "$LEGACY_RELATION_SCOPE" "eval_report_${mode}"
done

echo "[6/$TOTAL_STEPS] Evaluate diagnostics mode (full scope: $FULL_RELATION_SCOPE)"
for mode in strict relaxed; do
	run_eval_mode "$mode" "$FULL_RELATION_SCOPE" "eval_report_${mode}_fullscope"
done

echo "[7/$TOTAL_STEPS] Build concise baseline summary"
"$PYTHON_BIN" - <<PY
import json
from pathlib import Path

out_dir = Path("$OUT_DIR")
legacy_scope = "$LEGACY_RELATION_SCOPE"
full_scope = "$FULL_RELATION_SCOPE"
fallback_used = str("$FALLBACK_USED").lower() == "true"
strict_legacy = json.loads((out_dir / "eval_report_strict.json").read_text(encoding="utf-8"))
relaxed_legacy = json.loads((out_dir / "eval_report_relaxed.json").read_text(encoding="utf-8"))
strict_full = json.loads((out_dir / "eval_report_strict_fullscope.json").read_text(encoding="utf-8"))
relaxed_full = json.loads((out_dir / "eval_report_relaxed_fullscope.json").read_text(encoding="utf-8"))

legacy_micro = strict_legacy.get("aggregate", {}).get("micro", {})
full_micro = strict_full.get("aggregate", {}).get("micro", {})
legacy_strict = legacy_micro.get("strict", {})
legacy_relaxed = legacy_micro.get("relaxed", {})
full_strict = full_micro.get("strict", {})
full_relaxed = full_micro.get("relaxed", {})
scorecards = strict_legacy.get("scorecards", {})
tm = scorecards.get("time_ml_compliance", {})
bt = scorecards.get("beyond_timeml_reasoning", {})
suggestions = strict_legacy.get("diagnostics", {}).get("suggestions", [])

def layer_line(layer, strict_obj, relaxed_obj):
		return f"- {layer}: strict={float(strict_obj.get(layer, {}).get('f1', 0.0)):.4f}, relaxed={float(relaxed_obj.get(layer, {}).get('f1', 0.0)):.4f}"

lines = []
lines.append("# Cycle Summary")
lines.append("")
lines.append(f"- Documents evaluated: {strict_legacy.get('documents_evaluated', 0)}")
lines.append(f"- Script: scripts/run_meantime_eval_cycle.sh")
lines.append(f"- Legacy relation scope: {legacy_scope}")
lines.append(f"- Full relation scope: {full_scope}")
lines.append(f"- Fallback run used: {str(fallback_used).lower()}")
lines.append("")
lines.append("## Micro F1 (Legacy Scope)")
for layer in ("entity", "event", "timex", "relation"):
		lines.append(layer_line(layer, legacy_strict, legacy_relaxed))
lines.append("")
lines.append("## Micro F1 (Full Relation Scope)")
for layer in ("entity", "event", "timex", "relation"):
		lines.append(layer_line(layer, full_strict, full_relaxed))
lines.append("")
lines.append("## Scorecards (Legacy Scope)")
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

cycle_config = {
		"script": "scripts/run_meantime_eval_cycle.sh",
		"fallback_used": fallback_used,
		"runtime": {
				"python_bin": "$PYTHON_BIN",
				"dataset_dir": "$DATASET_DIR",
				"gold_dir": "$GOLD_DIR",
				"out_dir": "$OUT_DIR",
		},
		"legacy_relation_scope": legacy_scope,
		"full_relation_scope": full_scope,
		"reports": {
				"legacy": {
						"strict_json": "eval_report_strict.json",
						"relaxed_json": "eval_report_relaxed.json",
				},
				"fullscope": {
						"strict_json": "eval_report_strict_fullscope.json",
						"relaxed_json": "eval_report_relaxed_fullscope.json",
				},
		},
		"flags": {
				"normalize_nominal_boundaries": True,
				"nominal_precision_filters": True,
				"gold_like_nominal_filter": True,
		},
}
(out_dir / "cycle_config.json").write_text(json.dumps(cycle_config, indent=2), encoding="utf-8")
print((out_dir / "cycle_summary.md").as_posix())
PY

echo "Cycle complete. Artifacts: $OUT_DIR"
