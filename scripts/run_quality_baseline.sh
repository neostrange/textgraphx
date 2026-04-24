#!/usr/bin/env bash
# Capture a KG quality baseline snapshot.
#
# Usage:
#   bash scripts/run_quality_baseline.sh [--dataset-dir DIR] [--output-dir DIR]
#
# Writes JSON + CSV + Markdown into --output-dir (default: src/textgraphx/datastore/evaluation/baseline).
# The resulting kg_quality_report.json can be committed as the authoritative
# regression threshold for the CI quality gate check.

set -euo pipefail

DATASET_DIR="src/textgraphx/datastore/dataset"
OUTPUT_DIR="src/textgraphx/datastore/evaluation/baseline"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dataset-dir) DATASET_DIR="$2"; shift 2 ;;
        --output-dir)  OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Use the activated venv if present, otherwise fall back to PATH python.
PYTHON="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}"
PYTHON="${PYTHON:-python3}"

echo "=== textgraphx KG quality baseline ===" >&2
echo "  dataset : $DATASET_DIR" >&2
echo "  output  : $OUTPUT_DIR" >&2
echo "" >&2

mkdir -p "$OUTPUT_DIR"

COMPARE_ARGS=()
if [[ -f "$OUTPUT_DIR/kg_quality_report.json" ]]; then
    echo "  compare : $OUTPUT_DIR/kg_quality_report.json" >&2
    COMPARE_ARGS=(
        --baseline-report "$OUTPUT_DIR/kg_quality_report.json"
        --comparison-json "$OUTPUT_DIR/kg_quality_comparison.json"
    )
else
    echo "  compare : none (seed capture)" >&2
fi

"$PYTHON" -m textgraphx.tools.evaluate_kg_quality \
    --dataset-dir "$DATASET_DIR" \
    --output-dir  "$OUTPUT_DIR" \
    --snapshot-kind baseline \
    --json --csv --markdown \
    "${COMPARE_ARGS[@]}"

# Stamp the snapshot with the current git commit so baselines are traceable.
if command -v git &>/dev/null; then
    echo "$(git rev-parse HEAD 2>/dev/null || echo unknown)" > "$OUTPUT_DIR/baseline_commit.txt"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)"                  > "$OUTPUT_DIR/baseline_timestamp.txt"
fi

echo "" >&2
echo "Baseline written to $OUTPUT_DIR" >&2
if [[ -f "$OUTPUT_DIR/kg_quality_comparison.json" ]]; then
    echo "Baseline comparison written to $OUTPUT_DIR/kg_quality_comparison.json" >&2
fi
echo "Commit these files to lock quality thresholds for the gate check." >&2
