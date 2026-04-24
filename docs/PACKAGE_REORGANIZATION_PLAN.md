# Package Reorganization Plan

This document captures a concrete, incremental plan for reorganizing the
`textgraphx` repository so related code lives together and the package layout
communicates intent more clearly.

The goal is not a cosmetic rename sweep. The goal is to reduce the cognitive
load of navigating `src/textgraphx`, make ownership boundaries clearer, and
prepare the codebase for future feature work without repeatedly growing the
package root.

## Current Findings

### `src/textgraphx` mixes several distinct concerns at package root

The current package root contains at least six different categories of code:

1. Runtime and infrastructure
2. Pipeline phases and compatibility wrappers
3. Domain logic and reasoning helpers
4. Evaluation and quality tooling
5. Database and Cypher support
6. Data, docs, fixtures, notebooks, UI, and other non-runtime assets

This makes it difficult to answer basic navigation questions quickly, such as:

- where phase implementations live
- where runtime entrypoints live
- where Neo4j or Cypher concerns live
- where evaluation helpers end and production runtime begins
- which files are canonical versus backward-compatibility shims

### Major clusters already exist, but they are incomplete

The repo already has several good subpackages:

- `evaluation/`
- `orchestration/`
- `queries/`
- `schema/`
- `tools/`
- `text_processing_components/`

Those clusters show the natural shape of the codebase. The remaining problem is
that many root-level files still belong to one of those clusters or to new
clusters that do not exist yet.

### The package root has clear outliers

The following root-level modules are strong candidates to move into a more
specific package:

| Current file | Likely target package | Notes |
| --- | --- | --- |
| `EventEnrichmentPhase.py` | `pipeline/phases/` | Active phase implementation |
| `RefinementPhase.py` | `pipeline/phases/` | Active phase implementation |
| `TemporalPhase.py` | `pipeline/temporal/` | Active temporal phase |
| `TlinksRecognizer.py` | `pipeline/temporal/` | Temporal linking engine |
| `TextProcessor.py` | `pipeline/ingestion/` or `text_processing/` | Wraps lower-level processing components |
| `GraphBasedNLP.py` | `pipeline/ingestion/` | Legacy entry surface into processing pipeline |
| `phase_wrappers.py` | `pipeline/runtime/` or `orchestration/` | Runtime wrappers around phase execution |
| `phase_assertions.py` | `pipeline/runtime/` or `evaluation/diagnostics/` | Phase-level validation contract |
| `kg_quality_evaluation.py` | `evaluation/quality/` | Shared quality report helper |
| `diagnostics.py` | `evaluation/diagnostics/` | Runtime diagnostics registry/query helpers |
| `run_report.py` | `evaluation/reports/` | Runtime report artifact builder |
| `health_check.py` | `infrastructure/` | Deployment/runtime checks |
| `api.py` | `interfaces/api/` or `infrastructure/api/` | External API surface |
| `neo4j_client.py` | `database/` | Database connection factory |
| `cypher_optimizer.py` | `database/` | Query-level DB optimization |
| `checkpoint.py` | `orchestration/` | Execution lifecycle |
| `execution_history.py` | `orchestration/` | Execution lifecycle |
| `execution_summary.py` | `orchestration/` | Execution lifecycle |
| `scheduler.py` | `orchestration/` | Execution lifecycle |
| `provenance.py` | `reasoning/` | Domain reasoning helper |
| `authority.py` | `reasoning/` | Domain reasoning helper |
| `confidence.py` | `reasoning/` | Domain reasoning helper |
| `merge_utils.py` | `reasoning/` | Domain merge semantics |
| `reasoning_contracts.py` | `reasoning/` | Domain contract logic |
| `fusion.py` | `reasoning/` | Cross-document/entity reasoning |
| `temporal_constraints.py` | `reasoning/temporal/` | Temporal logic |
| `timeml_relations.py` | `reasoning/temporal/` | Temporal logic |
| `temporal_legacy_compat.py` | `reasoning/temporal/` | Compatibility shim |

### The repository root is also noisy

Outside `src/textgraphx`, the repository root currently mixes project metadata
with generated outputs and historical scratch artifacts, including:

- `audit_output.json`
- `bytecode.txt`
- `cycle_log*.txt`
- `doc_tokens.txt`
- `eval_*.json`
- `eval_*.csv`
- `report.txt`
- `rel_examples.txt`
- `MagicMock/`

Those files make the root harder to interpret and should not be treated as
structural examples when reorganizing the source tree.

## Constraints And Risks

### Compatibility wrappers exist and should be preserved during migration

Some root-level modules are already acting as compatibility surfaces. The most
obvious example is `PipelineOrchestrator.py`, which forwards to the canonical
implementation in `orchestration/orchestrator.py`.

That means a move should not immediately remove old import paths. The safe path
is:

1. move canonical implementation
2. leave a compatibility module or re-export in place
3. update internal imports gradually
4. remove compatibility paths only after tests and downstream consumers are updated

### Temporal files are higher risk than most other moves

`TemporalPhase.py`, `TlinksRecognizer.py`, and `temporal_legacy_compat.py`
carry legacy behavior and compatibility shims. They are natural candidates for a
subpackage, but they should not be the first move in a broad reorganization.

### `util/` and `utils/` are confusing and should converge carefully

There are currently two similarly named helper locations:

- `util/`
- `utils/`

`util/` holds external adapter-style modules such as REST callers and graph DB
base classes. `utils/` currently appears to hold a narrow helper surface.

These should not remain as two parallel naming patterns long term, but a rename
should happen only with explicit import compatibility handling.

## Proposed Target Hierarchy

The target layout below is intentionally conservative. It groups code by role,
while preserving room for compatibility shims during migration.

```text
src/textgraphx/
  infrastructure/
    api.py
    config.py
    health_check.py
    logging.py

  orchestration/
    orchestrator.py
    db_interface.py
    checkpoint.py
    execution_history.py
    execution_summary.py
    scheduler.py

  pipeline/
    phases/
      event_enrichment.py
      refinement.py
    temporal/
      extraction.py
      linking.py
      legacy.py
    ingestion/
      graph_based_nlp.py
      text_processor.py
    runtime/
      phase_wrappers.py
      phase_assertions.py

  text_processing/
    components/
      ... existing processing components ...
    llm/
    pipeline/

  adapters/
    rest_caller.py
    semantic_role_labeler.py
    entity_fishing.py
    graph_db_base.py
    allen_nlp_coref.py

  database/
    client.py
    cypher_optimizer.py
    queries/

  reasoning/
    authority.py
    confidence.py
    provenance.py
    merge_utils.py
    fusion.py
    contracts.py
    temporal/
      constraints.py
      relations.py
      legacy_compat.py

  evaluation/
    diagnostics/
      registry.py
    quality/
      kg_quality_evaluation.py
    reports/
      run_report.py
    ... existing evaluators ...

  interfaces/
    cli/
      ... if tools ever migrate under package interfaces ...

  tools/
  queries/
  schema/
  tests/
  datastore/
  docs/
```

## Recommended Grouping By Responsibility

### 1. Keep as-is

These areas already have strong cohesion and should not be the first place to
spend migration budget:

- `evaluation/`
- `orchestration/`
- `queries/`
- `schema/`
- `tools/`
- `text_processing_components/` as an internal cluster

### 2. Introduce new subpackages first

The two highest-value new packages are:

- `reasoning/`
- `pipeline/`

Those packages would absorb the largest set of semantically related root-level
files and reduce the cognitive load of the root directory the fastest.

### 3. Move runtime infrastructure out of root

The next most coherent cluster is infrastructure/runtime support:

- `api.py`
- `health_check.py`
- `config.py`
- logging helpers
- DB connection helpers

These should live in either `infrastructure/` or split between
`infrastructure/` and `database/`.

## Recommended Migration Order

This should be done in small phases, not one broad rename.

### Phase 0: Planning and compatibility policy

- decide canonical destination package names
- decide compatibility strategy for old imports
- document naming policy: snake_case package modules for new canonical locations

### Phase 1: Move low-risk infrastructure and support code

Suggested first moves:

- `checkpoint.py`
- `execution_history.py`
- `execution_summary.py`
- `scheduler.py`
- `neo4j_client.py`
- `cypher_optimizer.py`

Why first: these are structurally obvious, have narrower responsibilities, and
do not carry the same legacy behavioral risk as phase implementations.

### Phase 2: Consolidate domain reasoning helpers

Suggested moves into `reasoning/`:

- `authority.py`
- `confidence.py`
- `provenance.py`
- `merge_utils.py`
- `reasoning_contracts.py`
- `fusion.py`
- temporal reasoning helpers

Why second: these are strongly related by semantics and mostly logic-oriented.

### Phase 3: Consolidate quality and diagnostic surfaces

Suggested moves into `evaluation/` subpackages:

- `kg_quality_evaluation.py`
- `diagnostics.py`
- `run_report.py`

Why third: the evaluation cluster is already mature and these modules already
behave like evaluation-adjacent code.

### Phase 4: Consolidate pipeline runtime helpers

Suggested moves into `pipeline/runtime/`:

- `phase_assertions.py`
- `phase_wrappers.py`

Why fourth: these sit between orchestration and phase implementations, so it is
better to move them after the support layers around them are more stable.

### Phase 5: Move phase implementations

Suggested moves:

- `EventEnrichmentPhase.py`
- `RefinementPhase.py`
- `TemporalPhase.py`
- `TlinksRecognizer.py`
- `TextProcessor.py`
- `GraphBasedNLP.py`

Why fifth: this is the highest-risk set because of legacy class names,
compatibility surfaces, and broader import fan-out.

## Practical Safety Rules For The Refactor

1. Preserve import compatibility first.
   Leave wrappers or re-exports when moving canonical implementations.

2. Prefer moving one functional cluster per PR.
   Large cross-cutting renames will be harder to validate and review.

3. Do not mix naming normalization with package relocation in the same PR unless
   the cluster is tiny.

4. Validate with the narrowest cluster tests after each move.
   For example:
   - orchestration tests after moving execution/scheduling files
   - diagnostics and quality tests after moving evaluation helpers
   - temporal tests after moving temporal modules

5. Treat `tools/` as an external interface surface.
   If underlying modules move, preserve tool behavior first and update imports in
   a compatibility-safe way.

## Adjacent Cleanup Recommendations

### Repository root

The repo root should be reserved for project metadata and canonical entrypoints.

Generated evaluation/debug artifacts should instead live under:

- `out/`
- `src/textgraphx/datastore/evaluation/latest/`
- `src/textgraphx/datastore/evaluation/baseline/`

Historical scratch files at repo root should either be:

- moved under `out/` or an archival location
- ignored via `.gitignore`
- deleted if no longer part of a supported workflow

### `scripts/`

The `scripts/` area should distinguish clearly between:

- canonical runners
- operational wrappers
- historical one-off analysis scripts

If a script is now superseded by a stable CLI in `src/textgraphx/tools/`, it
should either be removed, archived, or explicitly documented as legacy.

## Suggested First Execution Slice

If this reorganization begins now, the best first implementation slice is:

1. create explicit target packages for `reasoning/`, `database/`, and
   `pipeline/runtime/`
2. move `checkpoint.py`, `execution_history.py`, `execution_summary.py`, and
   `scheduler.py` into `orchestration/`
3. preserve old import paths with compatibility wrappers or re-exports
4. run the orchestration-focused and runtime-history-focused tests

That slice is small enough to be safe, but meaningful enough to establish the
package migration pattern for later phases.

## Summary

The codebase does not need a total rewrite. It needs a staged re-homing of
root-level modules into clearer responsibility-based packages.

The main structural wins will come from:

- shrinking the `src/textgraphx` root
- making pipeline, reasoning, infrastructure, and evaluation explicit
- preserving legacy import stability while canonical locations improve
- cleaning generated noise out of the repository root so the true project
  structure is easier to read