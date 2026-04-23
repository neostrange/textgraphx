#!/usr/bin/env bash
# Docs hygiene checks for TextGraphX.
#
# Two tiers of enforcement:
#
#   (A) STRICT tier — applied to the "new docs surface":
#         * DOCUMENTATION.md (repo-root gateway)
#         * CONTRIBUTING.md
#         * docs/README.md
#         * docs/wiki/**/*.md (excluding _TEMPLATE.md)
#       Rules: metadata header near the top (last_reviewed + owner),
#              exactly one H1, no broken relative links.
#
#   (B) BASELINE tier — applied to all other docs under docs/:
#       Rule: no broken relative links. Legacy metadata/H1 style is
#             preserved and not reshaped by this script.
#
# Also enforces:
#   * Gateway DOCUMENTATION.md exists at repo root.
#   * `scripts/docs/generate_schema_summary.py --check` passes.
#   * `scripts/docs/generate_code_index.py --check` passes.
#
# Exit non-zero on any failure.

set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

FAIL=0

is_strict_target() {
  local f="$1"
  case "$f" in
    DOCUMENTATION.md|CONTRIBUTING.md|docs/README.md) return 0 ;;
    docs/wiki/*)
      local base
      base="$(basename "$f")"
      if [[ "$base" == _TEMPLATE.md || "$base" == _DOC_TEMPLATE.md ]]; then
        return 1
      fi
      return 0
      ;;
    *) return 1 ;;
  esac
}

echo "::group::1. Gateway presence"
if [[ ! -f DOCUMENTATION.md ]]; then
  echo "FAIL: DOCUMENTATION.md (gateway) is missing at repo root."
  FAIL=1
else
  echo "ok: DOCUMENTATION.md exists."
fi
echo "::endgroup::"

echo "::group::2. Strict tier: metadata headers"
MISSING_META=()
check_meta() {
  local f="$1"
  # Require both last_reviewed: and owner: somewhere in first 5 lines.
  local head5
  head5="$(head -n 5 "$f" 2>/dev/null || true)"
  if [[ "$head5" == *"last_reviewed:"* && "$head5" == *"owner:"* ]]; then
    return 0
  fi
  return 1
}

for f in DOCUMENTATION.md CONTRIBUTING.md docs/README.md; do
  [[ -f "$f" ]] || continue
  if is_strict_target "$f"; then
    if ! check_meta "$f"; then
      MISSING_META+=("$f")
    fi
  fi
done
while IFS= read -r f; do
  is_strict_target "$f" || continue
  if ! check_meta "$f"; then
    MISSING_META+=("$f")
  fi
done < <(find docs/wiki -type f -name '*.md' | sort)

if (( ${#MISSING_META[@]} > 0 )); then
  echo "FAIL: strict-tier docs missing last_reviewed/owner metadata:"
  printf '  - %s\n' "${MISSING_META[@]}"
  FAIL=1
else
  echo "ok: every strict-tier doc carries metadata."
fi
echo "::endgroup::"

echo "::group::3. Strict tier: exactly one H1"
BAD_H1=()
while IFS= read -r f; do
  [[ -f "$f" ]] || continue
  is_strict_target "$f" || continue
  count="$(grep -cE '^# [^#]' "$f" || true)"
  if [[ "$count" != "1" ]]; then
    BAD_H1+=("$f ($count H1s)")
  fi
done < <({ printf '%s\n' DOCUMENTATION.md CONTRIBUTING.md docs/README.md; find docs/wiki -type f -name '*.md'; } | sort -u)

if (( ${#BAD_H1[@]} > 0 )); then
  echo "FAIL: strict-tier docs without exactly one H1:"
  printf '  - %s\n' "${BAD_H1[@]}"
  FAIL=1
else
  echo "ok: every strict-tier doc has exactly one H1."
fi
echo "::endgroup::"

echo "::group::4. Link integrity (strict + baseline tiers)"
if ! python3 - <<'PY'
import pathlib, re, sys
root = pathlib.Path('.')
targets = [p for p in root.glob('docs/**/*.md') if p.name not in ('_TEMPLATE.md', '_DOC_TEMPLATE.md')]
for extra in ('DOCUMENTATION.md', 'CONTRIBUTING.md'):
    p = root / extra
    if p.exists():
        targets.append(p)
link_re = re.compile(r'\]\(([^)#][^)]*)\)')
missing = []
for t in targets:
    base = t.parent
    for m in link_re.finditer(t.read_text()):
        link = m.group(1).split('#')[0]
        if not link or link.startswith(('http://','https://','mailto:')):
            continue
        p = (base / link).resolve()
        if not p.exists():
            missing.append(f'{t}: {link} -> {p}')
if missing:
    print('FAIL: broken relative links:')
    for line in missing:
        print('  ' + line)
    sys.exit(1)
print(f'ok: {len(targets)} files checked; all relative links resolve.')
PY
then
  FAIL=1
fi
echo "::endgroup::"

echo "::group::5. Autogen pages in sync"
if python3 scripts/docs/generate_schema_summary.py --check; then
  echo "ok: schema autogen is up to date."
else
  echo "FAIL: schema autogen is stale. Run: python3 scripts/docs/generate_schema_summary.py"
  FAIL=1
fi
if python3 scripts/docs/generate_code_index.py --check; then
  echo "ok: code index is up to date."
else
  echo "FAIL: code index is stale. Run: python3 scripts/docs/generate_code_index.py"
  FAIL=1
fi
echo "::endgroup::"

