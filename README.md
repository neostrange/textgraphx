# textgraphx

textgraphx is an event-centric NLP-to-knowledge-graph pipeline that converts source documents into a Neo4j graph designed for temporal reasoning, semantic role analysis, and evaluation against MEANTIME-style gold standards.

## Why this project exists

The project turns unstructured text into a graph that is:
- explainable (token and span grounded)
- queryable (canonical labels and governed relations)
- testable (phase contracts + full evaluation harness)
- production-auditable (quality gates and run metadata)

## Architecture at a glance

Pipeline order:
1. ingestion (GraphBasedNLP and text processing components)
2. refinement (entity and mention normalization)
3. temporal extraction (TIMEX, TEvent, Signal, GLINK)
4. event enrichment (EventMention, participant linking)
5. TLINK recognition (temporal relation inference and consistency)

Primary references:
- `src/textgraphx/docs/architecture-overview.md`
- `src/textgraphx/docs/schema.md`
- `src/textgraphx/docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md`
- `src/textgraphx/docs/PROJECT_CONTEXT.md`

## Repository layout

- `src/textgraphx/`: importable package and runtime code
- `src/textgraphx/docs/`: architecture, schema, evaluation, and roadmap docs
- `src/textgraphx/tests/`: contract, regression, and integration tests
- `src/textgraphx/tools/`: operator and diagnostics CLIs
- `scripts/evaluation/`: curated evaluation scripts
- `scripts/archive/`: historical ad-hoc scripts kept for traceability
- `out/`: generated outputs (reports, checkpoints, run artifacts)

## Quick start

Install in editable mode with test extras:

```bash
python -m pip install -e .[test]
```

Run a non-integration test slice:

```bash
python -m pytest src/textgraphx/tests -q
```

Run pipeline:

```bash
python -m textgraphx.run_pipeline --dataset-dir src/textgraphx/datastore/dataset
```

## Testing strategy

Use tiered test execution for fast, reliable feedback:

1. Before structural refactors:
   - run contract and unit tests first (fast detection of path/import breaks)
2. During structural refactors:
   - run targeted tests for touched modules after each move
3. After structural refactors:
   - run broad non-integration suite
   - then run selected integration/e2e tests in a live Neo4j environment

Operational guidance and production checks:
- `src/textgraphx/docs/PRODUCTION_VALIDATION.md`
- `src/textgraphx/docs/RUNNING_PIPELINE.md`

## Version-control policy

Track in GitHub:
- source code, schema/migrations, tests, tools, scripts, and authored docs
- stable configuration templates and reproducibility metadata formats

Do not track generated artifacts:
- root-level eval JSON/CSV/log files
- temporary reports, local checkpoints, and runtime logs
- machine-local virtualenv and cache directories

See `.gitignore` for enforced rules.

## Roadmap context

Milestones M1-M8 establish a unified, self-certifying evaluation framework and MEANTIME bridge. M9-M10 focus on regression detection and CI quality gating.

Roadmap docs:
- `src/textgraphx/docs/EVALUATION_ROADMAP_M1_TO_M10.md`
- `src/textgraphx/docs/MILESTONE8_BRIDGE_VALIDATOR.md`
