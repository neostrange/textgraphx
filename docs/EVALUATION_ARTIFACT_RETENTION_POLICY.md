# Evaluation Artifact Retention Policy

This policy keeps repository history clean while preserving reproducibility.

## Goals

- keep evaluation code and workflows versioned
- avoid committing large, regenerable run artifacts
- retain only the minimum snapshots needed for regression comparisons

## Canonical Locations

- `src/textgraphx/datastore/evaluation/latest/`
	- mutable latest evaluation snapshot
	- overwritten by current runs
- `src/textgraphx/datastore/evaluation/baseline/`
	- curated baseline snapshots for comparison (including KG quality-gate baseline files)
	- update intentionally when a new baseline is accepted

## Git Policy

- keep `latest/` and `baseline/` only
- do not commit historical `cycle_*` outputs
- do not commit ad-hoc experiment dumps (`ab_*`, temporary sweeps, exploratory CSVs)
- CI guardrails enforce path and artifact hygiene on pull requests

This policy is enforced via `.gitignore` rules for `src/textgraphx/datastore/evaluation`.

## Operational Guidance

1. Use the cycle runner with the default `latest` tag for normal runs.
2. If you need a historical snapshot, export it externally (artifact store, release asset, or local archive), not in git.
3. Promote a baseline only when you intentionally accept quality changes.
4. Use `scripts/run_quality_baseline.sh` defaults unless you explicitly need an alternate output directory.

## Related Files

- `src/textgraphx/tools/evaluate_meantime.py`
- `src/textgraphx/scripts/run_meantime_eval_cycle.sh`
- `scripts/evaluation/README.md`
- `.gitignore`
- `.github/scripts/verify_structure_hygiene.sh`
- `.github/workflows/structure-guardrails.yml`
