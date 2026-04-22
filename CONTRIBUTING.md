# Contributing Guide

## Repository Layout

- Runtime package code lives under src/textgraphx.
- Tests live under src/textgraphx/tests.
- Canonical docs live under docs.
- Historical docs are under docs/archive.
- Curated operational scripts are under scripts.

## Path and Data Policy

- Use src-layout datastore paths in code and docs:
  - src/textgraphx/datastore/dataset
  - src/textgraphx/datastore/annotated
  - src/textgraphx/datastore/evaluation/latest
  - src/textgraphx/datastore/evaluation/baseline
- Do not use machine-local absolute paths in committed source/docs.

## Artifact and Git Hygiene

- Do not commit runtime checkpoints under out/checkpoints.
- Do not commit root-level generated evaluation artifacts (eval_*.json/log/csv, temporary logs, ad-hoc reports).
- Do not commit accidental dataset duplicates with " copy.naf" suffix.
- Keep evaluation baselines in src/textgraphx/datastore/evaluation/baseline.

## Documentation Hygiene

- Keep active runbooks concise and current in docs.
- Move historical implementation narratives to docs/archive.
- When relocating docs, update internal links to avoid dead references.

## Local Validation Before PR

Run at least:

```bash
bash .github/scripts/verify_structure_hygiene.sh
python -m pytest src/textgraphx/tests -q
```

For focused changes, run targeted tests for touched modules as well.

## Commit and PR Expectations

- Prefer small, reviewable commits with clear intent.
- Use descriptive commit messages (Conventional Commit style is preferred).
- In PR descriptions, include:
  - what changed
  - why it changed
  - how it was validated
