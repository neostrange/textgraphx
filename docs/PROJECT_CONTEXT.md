# Project Context and Repository Governance

This document captures the project context needed to make good structure and workflow decisions.

## 1) Project theme and objective

textgraphx is designed as a temporal, event-centric knowledge graph pipeline.

Core objective:
- convert source text to a graph suitable for temporal/event reasoning
- preserve span-grounded explainability
- support reproducible quality measurement against gold standards

This means architecture and repository choices should optimize for:
- semantic correctness over short-term convenience
- migration-safe evolution (canonical + legacy compatibility)
- high testability and quality-gate automation

## 2) Architecture model (operational)

Pipeline phases:
1. Ingestion: token/sentence graph, NER, SRL, coreference, lexical enrichment
2. Refinement: mention/entity normalization and semantic repair
3. Temporal: TIMEX/TEvent/Signal materialization and temporal anchors
4. Event enrichment: EventMention, frame-event mapping, participant wiring
5. TLINK recognizer: temporal relation inference, normalization, consistency checks

Design principles seen in code/docs:
- deterministic IDs for idempotent writes
- canonical-first read/write policy with legacy fallback during migration
- phase-run markers and diagnostics for observability

Primary references:
- architecture: `architecture-overview.md`
- schema contract: `schema.md`
- migration strategy: `schema-evolution-plan.md`

## 3) Schema model (canonical intent)

The schema is layered and governed:
- canonical tier: maintained semantic core used by runtime and evaluation
- optional tier: observability and enrichment signals
- legacy tier: compatibility during migration windows

Important schema posture:
- mention layer and canonical layer are explicitly separated where possible
- relation endpoint contracts are documented and testable
- temporal/event vocabulary is normalized for evaluation consistency

Practical implication for maintainers:
- prefer migrations + contract tests over ad-hoc schema drift
- update docs and tests when write paths change

## 4) Evaluation model (quality and reproducibility)

Evaluation stack:
- M1-M7: unified phase-level evaluation with validity headers and determinism metadata
- M8: MEANTIME bridge + cross-phase consistency validator
- M9-M10 (roadmap): regression baselines + CI quality gates

Output philosophy:
- reports should be self-certifying (run metadata, feature activation, reproducibility)
- generated evaluation outputs belong in evaluation output folders, not source annotation folders

## 5) When to run tests during structural work

Recommended timing:

1. Before major structure changes:
- run a fast baseline subset (contract/unit)
- capture known failures and expected skips

2. During structure changes:
- run focused tests for files moved or imports/path logic touched
- keep cycle short to isolate regressions quickly

3. After structure changes:
- run broad non-integration suite
- then run integration/e2e tests in a controlled environment (live Neo4j/services)

Why this ordering works:
- structure changes usually break paths/imports first
- broad runs are most valuable after path and packaging stabilization

## 6) GitHub tracking policy (context-specific)

Must track:
- runtime code under `src/textgraphx`
- schema and migrations
- curated tests and fixtures needed for deterministic validation
- authored docs and scripts that define process/quality

Optional track (team decision):
- stable baseline snapshots intentionally used for quality gates
- curated notebooks/examples used as long-term references

Do not track (generated/local):
- ad-hoc logs, temporary eval JSON/CSV at repo root
- machine-local caches/venvs
- one-off debug outputs and generated tool output files

## 7) Repository structure policy

Target structure already in use:
- `src/` layout for package isolation and reliable imports
- scripts split into maintained vs archived
- docs consolidated in one canonical location

Policy:
- avoid duplicate parallel directory trees at repository root
- keep one canonical location per content type
- archive experimentation scripts rather than deleting them

## 8) Roadmap-aware maintenance rules

When introducing new features/refactors:
- preserve compatibility where migrations are incomplete
- include contract tests for schema and phase behavior
- include evaluation impact assessment where event/relation behavior changes
- update this context document when governance or strategy changes
