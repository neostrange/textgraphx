#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [ -x "$ROOT_DIR/.venv310/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv310/bin/python"
elif [ -x "$ROOT_DIR/venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  PYTHON_BIN="python3"
fi

export TEXTGRAPHX_RUNTIME_MODE=testing
export TEXTGRAPHX_STRICT_TRANSITION_GATE=true

echo "Using Python: $PYTHON_BIN"
echo "TEXTGRAPHX_RUNTIME_MODE=$TEXTGRAPHX_RUNTIME_MODE"
echo "TEXTGRAPHX_STRICT_TRANSITION_GATE=$TEXTGRAPHX_STRICT_TRANSITION_GATE"

"$PYTHON_BIN" -m pytest \
  tests/test_phase_assertions.py \
  tests/test_orchestration.py \
  tests/test_regression_phases.py \
  tests/test_nominal_coverage_probe.py \
  tests/test_integration_nominal_coverage_probe.py \
  -q

echo "Review profile completed successfully."
