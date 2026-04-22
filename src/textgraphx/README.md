# textgraphx package

textgraphx is an event-centric NLP-to-knowledge-graph package that converts text into a Neo4j graph for temporal and relation reasoning.

This package README is intentionally concise for package consumers. The full project documentation and operational runbooks live in the repository-level docs.

## Why this package lives in src/textgraphx

This repository uses the standard Python src layout:
- package source is under src/textgraphx
- packaging metadata discovers modules from src
- repository root holds docs, scripts, and developer tooling

This layout is an industry best practice because it avoids import-path ambiguity during development and packaging.

## Install

```bash
python -m pip install -e .[test]
```

## Quick start

Run the pipeline:

```bash
python -m textgraphx.run_pipeline --dataset-dir src/textgraphx/datastore/dataset
```

Run MEANTIME evaluation:

```bash
python -m textgraphx.tools.evaluate_meantime \
  --gold-dir src/textgraphx/datastore/annotated \
  --pred-neo4j
```

## Artifact policy

Generated evaluation artifacts are retained in:
- src/textgraphx/datastore/evaluation/latest
- src/textgraphx/datastore/evaluation/baseline

Generated runtime outputs (for example out/checkpoints) are not part of the source of truth.

## Where to read more

- ../../README.md
- ../../docs/README.md
- ../../docs/architecture-overview.md
- ../../docs/schema.md
- ../../docs/EVALUATION_ARTIFACT_RETENTION_POLICY.md
