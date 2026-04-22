#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

failures=0

print_header() {
  echo
  echo "== $1 =="
}

report_failure() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

active_paths=(
  README.md
  docs
  src/textgraphx
  scripts/evaluation
  scripts/run_quality_baseline.sh
)

print_header "No machine-specific absolute paths"
abs_matches="$(grep -RIn "/home/neo/environments/textgraphx" "${active_paths[@]}" \
  --exclude-dir=.venv --exclude-dir=venv --exclude-dir=.venv310 --exclude-dir=__pycache__ || true)"
if [[ -n "$abs_matches" ]]; then
  echo "$abs_matches"
  report_failure "Found machine-specific absolute paths."
else
  echo "PASS"
fi

print_header "No legacy datastore paths"
legacy_matches="$(grep -RIn "textgraphx/datastore" "${active_paths[@]}" \
  --exclude-dir=.venv --exclude-dir=venv --exclude-dir=.venv310 --exclude-dir=__pycache__ | \
  grep -v "src/textgraphx/datastore" || true)"
if [[ -n "$legacy_matches" ]]; then
  echo "$legacy_matches"
  report_failure "Found legacy datastore paths that bypass src layout."
else
  echo "PASS"
fi

print_header "No tracked runtime checkpoints"
tracked_checkpoints="$(git ls-files out/checkpoints || true)"
if [[ -n "$tracked_checkpoints" ]]; then
  echo "$tracked_checkpoints"
  report_failure "Tracked files found under out/checkpoints."
else
  echo "PASS"
fi

print_header "No tracked out/evaluation artifacts"
tracked_out_evaluation="$(git ls-files out/evaluation || true)"
if [[ -n "$tracked_out_evaluation" ]]; then
  echo "$tracked_out_evaluation"
  report_failure "Tracked files found under out/evaluation; use src/textgraphx/datastore/evaluation instead."
else
  echo "PASS"
fi

print_header "No tracked duplicate dataset copy files"
tracked_copy_naf="$(git ls-files | grep -E '^src/textgraphx/datastore/.+ copy\.naf$' || true)"
if [[ -n "$tracked_copy_naf" ]]; then
  echo "$tracked_copy_naf"
  report_failure "Tracked dataset files with ' copy.naf' suffix found."
else
  echo "PASS"
fi

print_header "No tracked root-generated evaluation artifacts"
tracked_root_generated="$(git ls-files | grep -E '^(eval_.*\.(json|log|csv)|single_eval\.json|audit_output\.json|strict_events_summary\.json|cycle_log.*\.txt|doc_tokens\.txt|bytecode\.txt|report\.txt|rel_examples\.txt)$' || true)"
if [[ -n "$tracked_root_generated" ]]; then
  echo "$tracked_root_generated"
  report_failure "Tracked generated evaluation artifacts found at repository root."
else
  echo "PASS"
fi

if [[ "$failures" -gt 0 ]]; then
  echo
  echo "Structure hygiene checks failed: $failures issue(s)."
  exit 1
fi

echo
echo "All structure hygiene checks passed."
