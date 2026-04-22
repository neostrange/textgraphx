#!/usr/bin/env bash
set -euo pipefail

# Run the full TDD matrix in deterministic order.
# Usage:
#   bash scripts/run_tdd_matrix.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
	PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x "$ROOT_DIR/.venv310/bin/python" ]; then
	PYTHON_BIN="$ROOT_DIR/.venv310/bin/python"
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
	PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
	PYTHON_BIN="python3"
fi

if [ -x "$ROOT_DIR/.venv310/bin/python" ]; then
	INTEGRATION_PYTHON_BIN="$ROOT_DIR/.venv310/bin/python"
else
	INTEGRATION_PYTHON_BIN="$PYTHON_BIN"
fi

echo "Using Python: $PYTHON_BIN"
echo "Using Integration Python: $INTEGRATION_PYTHON_BIN"

echo "[1/5] Unit tests"
"$PYTHON_BIN" -m pytest -m unit --tb=short

echo "[2/5] Regression tests"
"$PYTHON_BIN" -m pytest -m regression --tb=short

echo "[3/5] Scenario tests"
"$PYTHON_BIN" -m pytest -m scenario --tb=short

echo "[4/5] Integration tests"
"$INTEGRATION_PYTHON_BIN" -m pytest -m integration --tb=short

echo "[4.5/5] Materialization gate regression"
"$INTEGRATION_PYTHON_BIN" -m pytest src/textgraphx/tests/test_integration_pipeline_materialization.py --tb=short

echo "[5/5] Smoke tests"
"$PYTHON_BIN" -m pytest src/textgraphx/tests/test_smoke_e2e.py -m slow --tb=short

echo "TDD matrix completed successfully."
