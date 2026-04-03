#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/venv"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

# activate venv
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# install deps
pip install -r "$ROOT/requirements.txt"

# install lightweight spaCy model (skip if already installed)
python -m spacy download en_core_web_sm || true

# defaults
DATASET="${1:-$ROOT/datastore/dataset}"
MODEL="${2:-sm}"

: "${NEO4J_URI:=bolt://localhost:7687}"
: "${NEO4J_USER:=neo4j}"
: "${NEO4J_PASSWORD:=neo4j}"

export NEO4J_URI NEO4J_USER NEO4J_PASSWORD

echo "Running GraphBasedNLP (model=$MODEL, dir=$DATASET)..."
python "$ROOT/GraphBasedNLP.py" --dir "$DATASET" --model "$MODEL"

echo "Running RefinementPhase..."
python "$ROOT/RefinementPhase.py"

echo "Running TemporalPhase..."
python "$ROOT/TemporalPhase.py"

echo "Running EventEnrichmentPhase..."
python "$ROOT/EventEnrichmentPhase.py"

echo "Running TlinksRecognizer..."
python "$ROOT/TlinksRecognizer.py"

echo "Pipeline complete."
