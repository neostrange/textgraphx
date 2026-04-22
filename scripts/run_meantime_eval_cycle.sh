#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CANONICAL_SCRIPT="$WORKSPACE_ROOT/textgraphx/scripts/run_meantime_eval_cycle.sh"

if [[ ! -x "$CANONICAL_SCRIPT" ]]; then
  echo "[ERROR] Canonical script not found or not executable: $CANONICAL_SCRIPT" >&2
  exit 1
fi

echo "[INFO] Delegating to repository script: textgraphx/scripts/run_meantime_eval_cycle.sh" >&2
exec "$CANONICAL_SCRIPT" "$@"
