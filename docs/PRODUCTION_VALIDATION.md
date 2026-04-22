# Production-Mode Validation Guide

This document describes how to validate a `textgraphx` pipeline deployment in
`runtime.mode=production` before promoting a build to production traffic.

## Why production mode is different

In `testing` mode the orchestrator clears the graph before every review run to
prevent corpus contamination.  In `production` mode that clearing step is
**skipped**; the pipeline fails fast instead if any pre-existing `AnnotatedText`
node is found with a conflicting document ID.

This means a misconfigured production run that is pointed at a stale or
partially-populated graph will raise an error rather than silently overwriting
data.

## Pre-flight checklist

Before a production run:

```
[ ] Neo4j is running and reachable at the configured bolt URL.
[ ] Config file has runtime.mode = production (or env TEXTGRAPHX_RUNTIME_MODE=production).
[ ] Graph is clean (or you deliberately intend to append to an existing corpus).
[ ] All required external services are reachable (temporal, SRL/coref/NER URLs).
[ ] Python 3.10 venv (.venv310) is active — spaCy requires CPython stdlib extensions
    (_ctypes, _sqlite3) that are absent from some Python 3.13 builds.
[ ] Dataset directory is populated (at least one .xml or .naf file).
```

## Running the production pipeline

```bash
# 1. Activate the 3.10 venv (required for spaCy phases).
source .venv310/bin/activate

# 2. Run the pipeline in production mode.
TEXTGRAPHX_RUNTIME_MODE=production python -m textgraphx.run_pipeline \
    --dataset-dir src/textgraphx/datastore/dataset \
    --cleanup none

# 3. Capture a post-run quality snapshot.
bash scripts/run_quality_baseline.sh \
    --dataset-dir src/textgraphx/datastore/dataset \
    --output-dir  out/evaluation/production-$(date -u +%Y%m%d)
```

## Post-run validation steps

### 1. Check the materialization gate

The orchestrator's materialization gate validates that all required node and
edge types were written.  A passing gate is a strong signal that all pipeline
phases executed correctly end-to-end.

If the gate fails, the run log will include a list of which node/edge type
counts were zero or below threshold.

### 2. Run the quality gate comparison

```bash
# Compare the post-run snapshot against the committed baseline.
python -m textgraphx.tools.check_quality_gate \
    --baseline src/textgraphx/datastore/evaluation/baseline/kg_quality_report.json \
    --current  out/evaluation/production-$(date -u +%Y%m%d)/kg_quality_report.json \
    --tolerance 0.02 \
    --max-tlink-anchor-inconsistent-increase 0 \
    --max-tlink-missing-anchor-metadata 0 \
    --max-participation-in-frame-missing-increase 0 \
    --max-participation-in-mention-missing-increase 0 \
    --max-participation-in-frame-missing 0 \
    --max-participation-in-mention-missing 0 \
    --verbose
```

A non-zero exit code means the overall quality score regressed more than the
allowed tolerance (2% by default), the TLINK anchor consistency thresholds
were violated, or participation-edge transition thresholds were violated
(`IN_FRAME` / `IN_MENTION` alias coverage regression).

### 3. Spot-check key node types

```cypher
-- Quick health check: counts of main node types
MATCH (n:AnnotatedText)   RETURN "AnnotatedText"  AS label, count(n) AS cnt
UNION MATCH (n:TEvent)    RETURN "TEvent"          AS label, count(n) AS cnt
UNION MATCH (n:TIMEX)     RETURN "TIMEX"           AS label, count(n) AS cnt
UNION MATCH (n:EventMention) RETURN "EventMention" AS label, count(n) AS cnt
UNION MATCH ()-[r:TLINK]->() RETURN "TLINK"        AS label, count(r) AS cnt
ORDER BY label
```

Expected (non-zero for each after a full run):
- `AnnotatedText` — one per document
- `TEvent` — typically 10–50 per document
- `TIMEX` — typically 2–15 per document
- `EventMention` — similar to TEvent
- `TLINK` — typically 5–30 per document

### 4. Run the schema validation tool

```bash
python -m textgraphx.tools.schema_validation --verbose
```

Any `ERROR`-level output indicates a schema contract violation that must be
resolved before the build is promoted.

### 5. Run UID contract validation

The mention identity contract is now enforced through live uniqueness
constraints on `NamedEntity.uid` and `EntityMention.uid`. Validate those
constraints directly against the target Neo4j graph before promotion.

Recommended commands:

```bash
# Preflight only: inspect constraints, null/blank UIDs, and duplicate UID groups.
make uid-preflight

# Or run the helper directly.
python \
    -m textgraphx.tools.uid_smoke_preflight \
    --preflight-only

# Optional smoke validation on a small document subset, with automatic cleanup.
make uid-smoke UID_DOCS=112579,113219,113227
```

Passing criteria:

- `NamedEntity.uid` uniqueness constraint is present
- `EntityMention.uid` uniqueness constraint is present
- null or blank UID counts are zero for both labels
- duplicate UID group counts are zero for both labels
- optional smoke-ingest completes and cleanup succeeds

Operational note:

- Use `.venv310` for this helper. The default `.venv` in this workspace is not
    reliable for spaCy-backed smoke runs because it is missing `_ctypes`.

### 6. Run the cross-phase consistency validator

```python
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.evaluation.cross_phase_validator import CrossPhaseValidator

graph = make_graph_from_config()
report = CrossPhaseValidator(graph).validate()
print(f"STATUS: {report.status}")
for v in report.violations:
    print(f"  [{v.severity}] {v.rule}: {v.message}")
```

The validator checks cascade semantics, density metrics, orphan detection, and
backward-compatibility edge ratios.  Any `ERROR`-level violation must be
investigated before promotion.

## Reverting a failed production run

If a production run leaves the graph in a partially-populated state:

```bash
# Full graph clear (destructive — confirm before running).
python -m textgraphx.tools.run_migrations --clear-all

# Alternatively, clear only the target document:
# MATCH (a:AnnotatedText {id: $doc_id})-[*0..10]->(n) DETACH DELETE n
```

After clearing, re-run from stage 1.

## Monitoring and alerting recommendations

| Signal | Threshold | Action |
|--------|-----------|--------|
| Quality gate delta | > −0.02 | Alert on-call, block promotion |
| Schema validation errors | any ERROR | Block promotion |
| Cross-phase ERRORs | any | Investigate before deploying |
| TEvent count per doc | < 5 | Investigate temporal phase |
| TLINK count per doc | 0 | Investigate TlinksRecognizer |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXTGRAPHX_RUNTIME_MODE` | `production` | `testing` clears graph before runs |
| `TEXTGRAPHX_STRICT_TRANSITION_GATE` | `false` | `true` enforces edge ratio thresholds |
| `TEXTGRAPHX_NEO4J_URL` | from config.ini | Bolt URL |
| `TEXTGRAPHX_NEO4J_USER` | from config.ini | Neo4j username |
| `TEXTGRAPHX_NEO4J_PASSWORD` | from config.ini | Neo4j password |
