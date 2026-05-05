#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x "$ROOT/.venv310/bin/python" ]; then
  PYTHON_BIN="$ROOT/.venv310/bin/python"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PYTHON_BIN="$ROOT/venv/bin/python"
else
  python3 -m venv "$ROOT/venv"
  PYTHON_BIN="$ROOT/venv/bin/python"
fi

# install deps
"$PYTHON_BIN" -m pip install -r "$ROOT/requirements.txt"

# defaults
DATASET="${1:-$ROOT/datastore/dataset}"
MODEL="${2:-trf}"

case "$MODEL" in
  trf|en_core_web_trf)
    SPACY_MODEL="en_core_web_trf"
    ;;
  sm|en_core_web_sm)
    SPACY_MODEL="en_core_web_sm"
    ;;
  md|en_core_web_md)
    SPACY_MODEL="en_core_web_md"
    ;;
  *)
    echo "Unsupported model '$MODEL'. Use trf|sm|md (or full spaCy model name)." >&2
    exit 2
    ;;
esac

# install requested spaCy model (skip hard-fail if already present/offline)
"$PYTHON_BIN" -m spacy download "$SPACY_MODEL" || true

: "${NEO4J_URI:=bolt://localhost:7687}"
: "${NEO4J_USER:=neo4j}"
: "${NEO4J_PASSWORD:=neo4j}"

export NEO4J_URI NEO4J_USER NEO4J_PASSWORD

echo "Running full pipeline review flow (model=$MODEL/$SPACY_MODEL, dir=$DATASET)..."
"$PYTHON_BIN" -m textgraphx.orchestration.orchestrator --dir "$DATASET" --model "$MODEL"

echo "Pipeline complete."
