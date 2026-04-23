<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

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
- Every new or renamed active doc must be reachable from [../DOCUMENTATION.md](DOCUMENTATION.md) and indexed in [docs/README.md](docs/README.md).
- New core docs should start from [docs/_DOC_TEMPLATE.md](docs/_DOC_TEMPLATE.md).
- New encyclopedia pages under `docs/wiki/**` must copy [docs/wiki/_TEMPLATE.md](docs/wiki/_TEMPLATE.md) and keep the metadata header (`last_reviewed`, `owner`, `status`).

## Docs-update-required rule (behavior changes)

Any PR that changes behavior in the following areas must also update at least one relevant doc in the same PR:

- Changes under `src/textgraphx/*Phase*.py`, `src/textgraphx/TlinksRecognizer.py`, `src/textgraphx/EventEnrichmentPhase.py`, `src/textgraphx/TemporalPhase.py`, `src/textgraphx/RefinementPhase.py`, `src/textgraphx/GraphBasedNLP.py`
  → update one of: [docs/architecture-overview.md](docs/architecture-overview.md), [docs/PIPELINE_INTEGRATION.md](docs/PIPELINE_INTEGRATION.md), or the relevant page under `docs/wiki/20-pipeline/` (once scaffolded).
- Changes under `src/textgraphx/schema/**` or `src/textgraphx/schema/ontology.json`
  → update one of: [docs/schema.md](docs/schema.md), [docs/schema-evolution-plan.md](docs/schema-evolution-plan.md), or the relevant page under `docs/wiki/40-ontology-and-schema/`.
- Changes under `src/textgraphx/evaluation/**` or `src/textgraphx/tools/check_quality_gate.py`
  → update the relevant evaluation doc under [docs/](docs/) or under `docs/wiki/55-evaluation-strategy/` (once scaffolded).

If a PR genuinely has no documentation impact, say so explicitly in the PR description (`Docs impact: none — <why>`). This rule will be enforced by a forthcoming CI check (`.github/scripts/verify_docs_hygiene.sh`).

## Changelog discipline

Every `CHANGELOG.md` entry either:

- links to the doc / wiki page it updates, or
- states `docs-only` / `no doc impact` with a one-line justification.

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
